from uuid import uuid4
from datetime import datetime, timezone

from app.cognitive.agents.planning_tools import (
    RoadmapBuilderTool,
    RoadmapBuilderInput,
    ScheduleGeneratorTool,
    ScheduleGeneratorInput,
    PortfolioProbeTool,
    PortfolioProbeInput,
)
from app.cognitive.contracts.types import (
    PlanOutline,
    PlanNode,
    PlanContext,
    StrategyProfile,
    Roadmap,
    Schedule,
)
from app.cognitive.agents.planning_controller import PlanningController
from app.cognitive.state.graph_state import GraphState


def _simple_outline_with_task():
    root_id = uuid4()
    task_id = uuid4()
    nodes = [
        PlanNode(
            id=root_id,
            parent_id=None,
            node_type="goal",
            level=1,
            title="Root Goal",
            status="pending",
            progress=0.0,
            origin="system",
            dependencies=[],
            tags=[],
            metadata={},
        ),
        PlanNode(
            id=task_id,
            parent_id=root_id,
            node_type="task",
            level=2,
            title="First Task",
            status="pending",
            progress=0.0,
            origin="system",
            dependencies=[],
            tags=[],
            metadata={},
        ),
    ]
    outline = PlanOutline(
        root_id=root_id,
        plan_context=PlanContext(strategy_profile=StrategyProfile(mode="manual")),
        nodes=nodes,
    )
    return outline


def test_roadmap_builder_minimal():
    outline = _simple_outline_with_task()
    tool = RoadmapBuilderTool()
    res = tool.run(RoadmapBuilderInput(outline=outline.model_dump(), roadmap_context={"scope": "test"}))
    assert res.ok, res.explanations
    roadmap = Roadmap.model_validate(res.data["roadmap"])  # type: ignore
    assert roadmap.root_id == outline.root_id
    assert len(roadmap.nodes) >= 1


def test_schedule_generator_minimal():
    outline = _simple_outline_with_task()
    rb = RoadmapBuilderTool().run(RoadmapBuilderInput(outline=outline.model_dump()))
    roadmap = Roadmap.model_validate(rb.data["roadmap"])  # type: ignore
    sg = ScheduleGeneratorTool()
    res = sg.run(ScheduleGeneratorInput(roadmap=roadmap.model_dump(), start_time=datetime.now(timezone.utc)))
    assert res.ok, res.explanations
    schedule = Schedule.model_validate(res.data["schedule"])  # type: ignore
    assert len(schedule.blocks) >= 1


def test_portfolio_probe_minimal():
    outline = _simple_outline_with_task()
    rb = RoadmapBuilderTool().run(RoadmapBuilderInput(outline=outline.model_dump()))
    roadmap = Roadmap.model_validate(rb.data["roadmap"])  # type: ignore
    sg = ScheduleGeneratorTool().run(ScheduleGeneratorInput(roadmap=roadmap.model_dump()))
    schedule = Schedule.model_validate(sg.data["schedule"])  # type: ignore
    pp = PortfolioProbeTool().run(PortfolioProbeInput(schedule=schedule.model_dump()))
    assert pp.ok, pp.explanations
    assert isinstance(pp.data.get("conflicts", []), list)


def test_planning_controller_smoke_runs():
    # Smoke test: controller should run and exit safely given stubs
    state = GraphState(goal_context={"description": "Test goal"})
    controller = PlanningController()
    new_state = controller.run(state)
    assert new_state is not None
    assert new_state.planning_status in {"needs_clarification", "aborted", "complete", "needs_scheduling_escalation"}
    assert isinstance(new_state.planning_trace, list)
