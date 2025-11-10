from __future__ import annotations

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class PatternTypeEnum(str, Enum):
    milestone_project = "milestone_project"
    recurring_cycle = "recurring_cycle"
    progressive_accumulation_arc = "progressive_accumulation_arc"
    hybrid_project_cycle = "hybrid_project_cycle"
    strategic_transformation = "strategic_transformation"
    # Allow learning_arc as subtype usually, but keep here if needed upstream


class PatternSpecSchema(BaseModel):
    pattern_type: PatternTypeEnum = Field(..., description="Canonical pattern type")
    subtype: Optional[str] = Field(None, description="Specific subtype or variant")
    variant: Optional[str] = Field(None, description="Variant label if any")
    confidence: float = Field(0.7, ge=0, le=1, description="Confidence in selection 0..1")


class NodeTypeEnum(str, Enum):
    goal = "goal"
    phase = "phase"
    cycle = "cycle"
    sub_goal = "sub_goal"
    task = "task"
    sub_task = "sub_task"
    micro_goal = "micro_goal"


class PlanNodeSchema(BaseModel):
    id: str = Field(..., min_length=6, max_length=64)
    parent_id: Optional[str] = Field(None)
    node_type: NodeTypeEnum
    level: int = Field(..., ge=1, le=8)
    title: str = Field(..., min_length=2, max_length=160)
    status: str = Field("pending")
    progress: float = Field(0.0, ge=0, le=1)
    dependencies: list[str] = Field(default_factory=list, min_length=0, max_length=12)
    tags: list[str] = Field(default_factory=list, min_length=0, max_length=12)
    notes: Optional[str] = Field(None, max_length=400)


class PlanOutlineSchema(BaseModel):
    root_id: str = Field(..., description="ID of root goal node")
    nodes: list[PlanNodeSchema] = Field(..., min_length=1, max_length=120)
    # pattern can be attached externally in our internal type; omit here for simplicity
