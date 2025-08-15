# app/cognitive/world/query.py
"""
Query module for the cognitive assistant. This module handles all queries related to the user's world state, 
including task scheduling, availability, and semantic slot ranking.
"""

from typing import List, Optional
from datetime import datetime, date, time, timedelta
from enum import Enum

from pydantic import BaseModel, Field
from .state import CalendarizedTask, WorldState, TimeRange


class SlotSearchMode(str, Enum):
    """Different modes for slot searching"""
    NEXT_AVAILABLE = "next_available"  # Find the very next slot
    ALL_TODAY = "all_today"           # All slots for today
    ALL_DATE = "all_date"             # All slots for specific date
    DATE_RANGE = "date_range"         # All slots in date range
    BEST_FIT = "best_fit"             # Optimal slot considering preferences


class TimeSlot(BaseModel):
    """Represents an available time slot"""
    start_datetime: datetime
    end_datetime: datetime
    duration_minutes: int
    date: date
    start_time: time
    end_time: time
    
    # Metadata
    day_of_week: str
    is_morning: bool = False
    is_afternoon: bool = False
    is_evening: bool = False
    
    # Quality indicators
    conflicts_nearby: int = 0  # Number of tasks within 1 hour
    capacity_load: float = 0.0  # How loaded the day is (0.0-1.0)
    
    # Semantic quality indicators
    energy_score: float = 0.0  # How good this time is for high-energy tasks (0.0-1.0)
    focus_score: float = 0.0   # How good this time is for deep focus (0.0-1.0)
    creativity_score: float = 0.0  # How good this time is for creative work (0.0-1.0)
    
    @classmethod
    def from_datetime_range(cls, start_dt: datetime, end_dt: datetime) -> "TimeSlot":
        """Create TimeSlot from datetime range"""
        duration = int((end_dt - start_dt).total_seconds() / 60)
        
        slot = cls(
            start_datetime=start_dt,
            end_datetime=end_dt,
            duration_minutes=duration,
            date=start_dt.date(),
            start_time=start_dt.time(),
            end_time=end_dt.time(),
            day_of_week=start_dt.strftime('%A'),
            is_morning=start_dt.hour < 12,
            is_afternoon=12 <= start_dt.hour < 17,
            is_evening=start_dt.hour >= 17
        )
        
        # Calculate semantic scores based on time patterns
        slot._calculate_semantic_scores()
        return slot
    
    def _calculate_semantic_scores(self):
        """Calculate semantic quality scores based on research-backed time patterns"""
        hour = self.start_time.hour
        
        # Energy score: Peak energy typically 9-11 AM and 2-4 PM
        if 9 <= hour <= 11:
            self.energy_score = 1.0  # Peak morning energy
        elif 14 <= hour <= 16:
            self.energy_score = 0.85  # Afternoon energy boost
        elif 8 <= hour <= 9 or 11 <= hour <= 14:
            self.energy_score = 0.7  # Good energy
        elif 16 <= hour <= 18:
            self.energy_score = 0.6  # Declining energy
        else:
            self.energy_score = 0.3  # Low energy periods
        
        # Focus score: Deep focus best in morning and late afternoon
        if 9 <= hour <= 11:
            self.focus_score = 1.0  # Peak focus time
        elif 8 <= hour <= 9:
            self.focus_score = 0.8  # Good morning focus
        elif 15 <= hour <= 17:
            self.focus_score = 0.75  # Afternoon focus
        elif 7 <= hour <= 8 or 11 <= hour <= 13:
            self.focus_score = 0.6  # Moderate focus
        else:
            self.focus_score = 0.4  # Lower focus periods
        
        # Creativity score: Often peaks mid-morning and evening
        if 10 <= hour <= 12:
            self.creativity_score = 1.0  # Peak creative time
        elif 19 <= hour <= 21:
            self.creativity_score = 0.9  # Evening creativity
        elif 8 <= hour <= 10 or 14 <= hour <= 16:
            self.creativity_score = 0.7  # Good creative periods
        elif 16 <= hour <= 19:
            self.creativity_score = 0.6  # Moderate creativity
        else:
            self.creativity_score = 0.4  # Lower creativity periods


class SlotQuery(BaseModel):
    """Query parameters for finding available slots"""
    duration_minutes: int
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    earliest_time: Optional[time] = None  # e.g., 9:00 AM
    latest_time: Optional[time] = None    # e.g., 6:00 PM
    preferred_times: List[time] = Field(default_factory=list)  # Preferred start times
    preferred_parts_of_day: List[str] = Field(default_factory=list)  # "morning", "afternoon", "evening"
    exclude_weekends: bool = False
    mode: SlotSearchMode = SlotSearchMode.NEXT_AVAILABLE
    max_results: int = 10
    
    # Advanced constraints
    min_buffer_minutes: int = 0  # Minimum gap from existing tasks
    respect_capacity: bool = True
    respect_blackouts: bool = True
    
    # Semantic ranking
    task_type: Optional[str] = None  # "creative", "analytical", "administrative", "physical", "social"
    energy_level_required: Optional[str] = None  # "high", "medium", "low"
    focus_level_required: Optional[str] = None  # "deep", "moderate", "light"


class SlotQueryResult(BaseModel):
    """Result of a slot search query"""
    query: SlotQuery
    slots: List[TimeSlot] = Field(default_factory=list)
    total_found: int = 0
    search_range_days: int = 0
    constraints_applied: List[str] = Field(default_factory=list)
    
    # Performance metadata
    search_time_ms: float = 0.0
    world_state_version: str = "1.0"


class WorldQueryEngine:
    """
    Intelligent time slot discovery engine.
    Scans WorldState to find available time slots with full constraint awareness.
    """
    
    def __init__(self, world_state: WorldState):
        self.world_state = world_state
        # Performance optimization: cache tasks by date
        self._task_cache = {}
        self._cache_version = None
    
    def find_next_free_slot(self, duration_minutes: int, after_datetime: Optional[datetime] = None) -> Optional[TimeSlot]:
        """
        Find the very next available slot of specified duration
        
        Args:
            duration_minutes: Required slot duration
            after_datetime: Search after this time (default: now)
            
        Returns:
            Next available TimeSlot or None if not found in reasonable timeframe
        """
        if after_datetime is None:
            after_datetime = datetime.now()
        
        query = SlotQuery(
            duration_minutes=duration_minutes,
            start_date=after_datetime.date(),
            mode=SlotSearchMode.NEXT_AVAILABLE,
            max_results=1
        )
        
        result = self.find_available_slots(query, after_datetime=after_datetime)
        return result.slots[0] if result.slots else None
    
    def find_slots_on_date(self, target_date: date, duration_minutes: int) -> List[TimeSlot]:
        """
        Find all available slots on a specific date
        
        Args:
            target_date: Date to search
            duration_minutes: Required slot duration
            
        Returns:
            List of available TimeSlots on that date
        """
        query = SlotQuery(
            duration_minutes=duration_minutes,
            start_date=target_date,
            end_date=target_date,
            mode=SlotSearchMode.ALL_DATE,
            max_results=50
        )
        
        result = self.find_available_slots(query)
        return result.slots
    
    def find_slots_in_range(self, start_date: date, end_date: date, duration_minutes: int) -> List[TimeSlot]:
        """
        Find all available slots within a date range
        
        Args:
            start_date: Start of search range
            end_date: End of search range
            duration_minutes: Required slot duration
            
        Returns:
            List of available TimeSlots in the range
        """
        query = SlotQuery(
            duration_minutes=duration_minutes,
            start_date=start_date,
            end_date=end_date,
            mode=SlotSearchMode.DATE_RANGE,
            max_results=100
        )
        
        result = self.find_available_slots(query)
        return result.slots
    
    def can_fit_task_on_date(self, target_date: date, duration_minutes: int, 
                           earliest_time: Optional[time] = None, 
                           latest_time: Optional[time] = None) -> bool:
        """
        Check if a task can fit anywhere on a specific date
        
        Args:
            target_date: Date to check
            duration_minutes: Required duration
            earliest_time: Earliest acceptable start time
            latest_time: Latest acceptable start time
            
        Returns:
            True if task can fit, False otherwise
        """
        query = SlotQuery(
            duration_minutes=duration_minutes,
            start_date=target_date,
            end_date=target_date,
            earliest_time=earliest_time,
            latest_time=latest_time,
            max_results=1
        )
        
        result = self.find_available_slots(query)
        return len(result.slots) > 0
    
    def find_available_slots(self, query: SlotQuery, after_datetime: Optional[datetime] = None) -> SlotQueryResult:
        """
        Core slot finding algorithm with full constraint awareness
        
        Args:
            query: Slot search parameters
            after_datetime: Start search after this time
            
        Returns:
            SlotQueryResult with found slots and metadata
        """
        start_time = datetime.now()
        
        # Validate query parameters
        if query.duration_minutes <= 0:
            return SlotQueryResult(
                query=query,
                slots=[],
                total_found=0,
                constraints_applied=["Invalid duration: must be greater than 0"]
            )
        
        # Determine search range
        search_start_date = query.start_date or (after_datetime or datetime.now()).date()
        search_end_date = query.end_date or (search_start_date + timedelta(days=14))  # Default 2 weeks
        
        slots = []
        constraints_applied = []
        
        # Search each day in the range
        current_date = search_start_date
        while current_date <= search_end_date and len(slots) < query.max_results:
            if query.exclude_weekends and current_date.weekday() >= 5:
                current_date += timedelta(days=1)
                continue
            
            # Get available time ranges for this date
            available_ranges = self._get_available_ranges_for_date(current_date)
            
            # Find slots within each available range
            for time_range in available_ranges:
                day_slots = self._find_slots_in_time_range(
                    current_date, time_range, query, after_datetime
                )
                slots.extend(day_slots)
                
                # Early exit for NEXT_AVAILABLE mode
                if query.mode == SlotSearchMode.NEXT_AVAILABLE and slots:
                    break
                
                # Early exit if we have enough results
                if len(slots) >= query.max_results:
                    break
            
            if query.mode == SlotSearchMode.NEXT_AVAILABLE and slots:
                break
                
            current_date += timedelta(days=1)
        
        # Apply additional constraints and scoring
        filtered_slots = self._apply_constraints_and_score(slots, query, constraints_applied)
        
        # Sort and limit results
        sorted_slots = self._sort_slots(filtered_slots, query)
        final_slots = sorted_slots[:query.max_results]
        
        # Calculate performance metrics
        search_time_ms = (datetime.now() - start_time).total_seconds() * 1000
        search_range_days = (search_end_date - search_start_date).days + 1
        
        return SlotQueryResult(
            query=query,
            slots=final_slots,
            total_found=len(final_slots),
            search_range_days=search_range_days,
            constraints_applied=constraints_applied,
            search_time_ms=search_time_ms,
            world_state_version=self.world_state.version
        )
    
    def _get_available_ranges_for_date(self, target_date: date) -> List[TimeRange]:
        """Get available time ranges for a specific date"""
        # Check for blackout windows first
        for blackout in self.world_state.blackouts:
            if blackout.start_datetime.date() <= target_date <= blackout.end_datetime.date():
                return []  # No availability during blackout periods
        
        # Check for date-specific availability
        for day_availability in self.world_state.availability.date_specific:
            if day_availability.date == target_date:
                if day_availability.is_blackout:
                    return []  # No availability on blackout days
                return day_availability.available_ranges
        
        # Fall back to default weekly pattern
        weekday = target_date.strftime('%A').lower()
        if weekday in self.world_state.availability.default_weekly_pattern:
            return self.world_state.availability.default_weekly_pattern[weekday]
        
        # No availability pattern defined - assume 9AM-6PM
        return [TimeRange(start_time=time(9, 0), end_time=time(18, 0))]
    
    def _find_slots_in_time_range(self, target_date: date, time_range: TimeRange, 
                                query: SlotQuery, after_datetime: Optional[datetime]) -> List[TimeSlot]:
        """Find available slots within a specific time range on a date"""
        slots = []
        
        # Convert time range to datetime
        range_start = datetime.combine(target_date, time_range.start_time)
        range_end = datetime.combine(target_date, time_range.end_time)
        
        # Handle ranges that span midnight
        if time_range.end_time < time_range.start_time:
            range_end += timedelta(days=1)
        
        # Apply after_datetime constraint
        if after_datetime and range_start < after_datetime:
            range_start = after_datetime
        
        # Apply query time constraints
        if query.earliest_time:
            earliest_dt = datetime.combine(target_date, query.earliest_time)
            range_start = max(range_start, earliest_dt)
        
        if query.latest_time:
            latest_dt = datetime.combine(target_date, query.latest_time)
            range_end = min(range_end, latest_dt)
        
        # Check if we have enough time left
        if (range_end - range_start).total_seconds() < query.duration_minutes * 60:
            return slots
        
        # Get existing tasks for this date
        existing_tasks = self._get_tasks_for_date(target_date)
        existing_tasks.sort(key=lambda t: t.start_datetime)
        
        # Find gaps between tasks
        current_time = range_start
        
        for task in existing_tasks:
            # Skip tasks outside our time range
            if task.end_datetime <= range_start or task.start_datetime >= range_end:
                continue
            
            # Check gap before this task
            gap_end = min(task.start_datetime, range_end)
            if query.min_buffer_minutes > 0:
                gap_end -= timedelta(minutes=query.min_buffer_minutes)
            
            gap_duration = (gap_end - current_time).total_seconds() / 60
            
            if gap_duration >= query.duration_minutes:
                # Found a viable gap - create slot
                slot_end = current_time + timedelta(minutes=query.duration_minutes)
                slot = TimeSlot.from_datetime_range(current_time, slot_end)
                slots.append(slot)
                
                # Advance current_time to prevent overlapping slots
                current_time = slot_end
                if query.min_buffer_minutes > 0:
                    current_time += timedelta(minutes=query.min_buffer_minutes)
            
            # Move past this task with buffer
            next_start = task.end_datetime
            if query.min_buffer_minutes > 0:
                next_start += timedelta(minutes=query.min_buffer_minutes)
            current_time = max(current_time, next_start)
        
        # Check final gap after all tasks
        if current_time < range_end:
            gap_duration = (range_end - current_time).total_seconds() / 60
            if gap_duration >= query.duration_minutes:
                slot_end = current_time + timedelta(minutes=query.duration_minutes)
                slot = TimeSlot.from_datetime_range(current_time, slot_end)
                slots.append(slot)
        
        return slots
    
    def _get_tasks_for_date(self, target_date: date) -> List[CalendarizedTask]:
        """Get all tasks scheduled for a specific date (cached for performance)"""
        # Check if cache is still valid
        if self._cache_version != self.world_state.version:
            self._task_cache.clear()
            self._cache_version = self.world_state.version
        
        # Check cache first
        date_str = target_date.isoformat()
        if date_str in self._task_cache:
            return self._task_cache[date_str]
        
        # Build task list for this date
        tasks = []
        for task in self.world_state.all_tasks:
            # Skip tasks with invalid duration
            if not hasattr(task, 'estimated_minutes') or task.estimated_minutes <= 0:
                continue
                
            task_date = task.start_datetime.date()
            # Include tasks that might span into this date
            if task_date == target_date or (
                task_date < target_date and task.end_datetime.date() >= target_date
            ):
                tasks.append(task)
        
        # Cache the result
        self._task_cache[date_str] = tasks
        return tasks
    
    def _apply_constraints_and_score(self, slots: List[TimeSlot], query: SlotQuery, 
                                   constraints_applied: List[str]) -> List[TimeSlot]:
        """Apply additional constraints and calculate quality scores"""
        filtered_slots = []
        
        for slot in slots:
            # Check capacity constraints
            if query.respect_capacity and self._would_exceed_capacity(slot):
                constraints_applied.append(f"Capacity limit on {slot.date}")
                continue
            
            # Calculate quality indicators
            slot.conflicts_nearby = self._count_nearby_conflicts(slot)
            slot.capacity_load = self._calculate_day_capacity_load(slot.date)
            
            filtered_slots.append(slot)
        
        return filtered_slots
    
    def _would_exceed_capacity(self, slot: TimeSlot) -> bool:
        """Check if adding this slot would exceed capacity limits"""
        date_str = slot.date.isoformat()
        current_load = self.world_state.capacity.current_daily_load.get(date_str, 0.0)
        slot_hours = slot.duration_minutes / 60.0
        daily_limit = self.world_state.capacity.constraints.max_hours_per_day
        
        return current_load + slot_hours > daily_limit
    
    def _count_nearby_conflicts(self, slot: TimeSlot) -> int:
        """Count tasks within 1 hour of this slot"""
        count = 0
        buffer = timedelta(hours=1)
        
        for task in self.world_state.all_tasks:
            # Check if task is on the same date
            if task.start_datetime.date() != slot.date:
                continue
            
            # Check if task is within buffer zone
            if (task.start_datetime <= slot.end_datetime + buffer and
                task.end_datetime >= slot.start_datetime - buffer):
                count += 1
        
        return count
    
    def _calculate_day_capacity_load(self, target_date: date) -> float:
        """Calculate how loaded a day is (0.0 = empty, 1.0 = at capacity)"""
        date_str = target_date.isoformat()
        current_load = self.world_state.capacity.current_daily_load.get(date_str, 0.0)
        daily_limit = self.world_state.capacity.constraints.max_hours_per_day
        
        return min(current_load / daily_limit, 1.0) if daily_limit > 0 else 0.0
    
    def _sort_slots(self, slots: List[TimeSlot], query: SlotQuery) -> List[TimeSlot]:
        """Sort slots by preference using semantic ranking"""
        def slot_score(slot: TimeSlot) -> float:
            score = 0.0
            
            # Semantic scoring based on task requirements (higher weights for semantic factors)
            semantic_score = 0.0
            
            # Task type preferences (significantly boost semantic relevance)
            if query.task_type:
                if query.task_type == "creative":
                    semantic_score += slot.creativity_score * 500  # Heavy weight for creativity
                    semantic_score += slot.energy_score * 200     # Some energy needed
                elif query.task_type == "analytical":
                    semantic_score += slot.focus_score * 500      # Deep focus critical
                    semantic_score += slot.energy_score * 300     # High energy helps
                elif query.task_type == "administrative":
                    semantic_score += slot.energy_score * 200     # Moderate requirements
                    semantic_score += slot.focus_score * 100      # Some focus needed
                elif query.task_type == "physical":
                    semantic_score += slot.energy_score * 600     # High energy critical
                elif query.task_type == "social":
                    semantic_score += slot.energy_score * 200     # Energy for interaction
                    # Social tasks often better afternoon/evening
                    if slot.is_afternoon or slot.is_evening:
                        semantic_score += 200
            
            # Energy level requirements (high boost for matching requirements)
            if query.energy_level_required:
                if query.energy_level_required == "high":
                    semantic_score += slot.energy_score * 400
                elif query.energy_level_required == "medium":
                    semantic_score += slot.energy_score * 200
                # Low energy tasks don't need energy bonus
            
            # Focus level requirements (high boost for matching requirements)
            if query.focus_level_required:
                if query.focus_level_required == "deep":
                    semantic_score += slot.focus_score * 400
                elif query.focus_level_required == "moderate":
                    semantic_score += slot.focus_score * 200
                # Light focus tasks don't need focus bonus
            
            score += semantic_score
            
            # Prefer earlier times for NEXT_AVAILABLE (lower weight when semantic factors present)
            if query.mode == SlotSearchMode.NEXT_AVAILABLE:
                time_bonus = 100 if semantic_score == 0 else 50  # Reduce influence when semantic factors present
                score += time_bonus - (slot.start_datetime.timestamp() / 10000)
            
            # Prefer preferred times
            for pref_time in query.preferred_times:
                time_diff = abs((slot.start_time.hour * 60 + slot.start_time.minute) - 
                              (pref_time.hour * 60 + pref_time.minute))
                score += max(0, 720 - time_diff)  # Max 12 hours = 720 minutes
            
            # Prefer preferred parts of day
            for part in query.preferred_parts_of_day:
                if part.lower() == "morning" and slot.is_morning:
                    score += 200
                elif part.lower() == "afternoon" and slot.is_afternoon:
                    score += 200
                elif part.lower() == "evening" and slot.is_evening:
                    score += 200
            
            # Quality penalties (reduced impact when semantic factors present)
            conflict_penalty = slot.conflicts_nearby * (20 if semantic_score == 0 else 10)
            load_penalty = slot.capacity_load * (50 if semantic_score == 0 else 25)
            
            score -= conflict_penalty
            score -= load_penalty
            
            return score
        
        return sorted(slots, key=slot_score, reverse=True)


# === CONVENIENCE FUNCTIONS ===

def find_next_free_slot(world_state: WorldState, duration_minutes: int, 
                       after_datetime: Optional[datetime] = None) -> Optional[TimeSlot]:
    """Convenience function to find the next available slot"""
    engine = WorldQueryEngine(world_state)
    return engine.find_next_free_slot(duration_minutes, after_datetime)


def find_slots_today(world_state: WorldState, duration_minutes: int) -> List[TimeSlot]:
    """Convenience function to find all slots available today"""
    engine = WorldQueryEngine(world_state)
    return engine.find_slots_on_date(date.today(), duration_minutes)


def find_slots_this_week(world_state: WorldState, duration_minutes: int) -> List[TimeSlot]:
    """Convenience function to find all slots available this week"""
    today = date.today()
    week_end = today + timedelta(days=7)
    
    engine = WorldQueryEngine(world_state)
    return engine.find_slots_in_range(today, week_end, duration_minutes)
