"""stock_hub.services.stock_analysis_runner 单元测试。"""

import time

from domains.stock_hub.services.stock_analysis_runner import StockAnalysisRunner


class FakeAnalysisService:
    """用于测试执行器的假服务。"""

    def run_enhanced_analysis(self, **kwargs):
        if kwargs["factor_name"] == "bad_factor":
            return {"error": "分析失败"}
        return {"factor_name": kwargs["factor_name"], "score": 1.0}

    def run_dual_analysis(self, **kwargs):
        return {
            "main_factor": kwargs["main_factor"],
            "sub_factor": kwargs["sub_factor"],
            "heatmaps": {},
        }


def _wait_for_terminal_status(runner: StockAnalysisRunner, task_id: str) -> str:
    deadline = time.time() + 2
    while time.time() < deadline:
        task = runner.get_status(task_id)
        if task is not None and task.status in {"completed", "failed"}:
            return task.status
        time.sleep(0.01)
    raise AssertionError("任务在超时时间内未结束")


def test_submit_enhanced_analysis_task_success():
    """增强分析任务成功完成。"""
    runner = StockAnalysisRunner(service=FakeAnalysisService(), max_workers=1)

    task_id = runner.submit_enhanced(
        factor_name="factor_市值",
        period_offset_list=["5_0"],
    )
    final_status = _wait_for_terminal_status(runner, task_id)

    task = runner.get_status(task_id)
    assert final_status == "completed"
    assert task is not None
    assert task.task_type == "enhanced"
    assert runner.get_result(task_id) == {"factor_name": "factor_市值", "score": 1.0}


def test_submit_enhanced_analysis_task_failure():
    """分析服务返回 error 时，任务标记为失败。"""
    runner = StockAnalysisRunner(service=FakeAnalysisService(), max_workers=1)

    task_id = runner.submit_enhanced(
        factor_name="bad_factor",
        period_offset_list=["5_0"],
    )
    final_status = _wait_for_terminal_status(runner, task_id)

    task = runner.get_status(task_id)
    assert final_status == "failed"
    assert task is not None
    assert task.error_message == "分析失败"


def test_submit_dual_analysis_task_success():
    """双因子任务成功完成。"""
    runner = StockAnalysisRunner(service=FakeAnalysisService(), max_workers=1)

    task_id = runner.submit_dual(
        main_factor="factor_a",
        sub_factor="factor_b",
        period_offset_list=["5_0"],
    )
    final_status = _wait_for_terminal_status(runner, task_id)

    task = runner.get_status(task_id)
    assert final_status == "completed"
    assert task is not None
    assert task.task_type == "dual"
    assert runner.get_result(task_id) == {
        "main_factor": "factor_a",
        "sub_factor": "factor_b",
        "heatmaps": {},
    }
