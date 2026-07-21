"""In-memory customers used only to demonstrate W2 daily aggregation."""

from copy import deepcopy
from typing import Any


MOCK_CUSTOMERS: list[dict[str, Any]] = [
    {
        "name": "王经理",
        "industry": "企业软件",
        "stage": "方案比较阶段",
        "need": "比较 AI 客户跟进工具与现有 CRM 的差异",
        "concerns": ["数据安全", "部署成本", "团队培训"],
        "opportunity_level": "中高",
        "todo": "补充方案对比材料，确认决策流程",
        "risk": "客户对数据安全要求较高，需明确权限与数据处理边界",
    },
    {
        "name": "陈老师",
        "industry": "职业教育",
        "stage": "初步咨询阶段",
        "need": "提升课程顾问对学员咨询的跟进效率",
        "concerns": ["话术质量", "使用门槛", "是否适合新人顾问"],
        "opportunity_level": "中",
        "todo": "发送需求确认问题清单",
        "risk": "需求较宽泛，尚未明确预算与试用范围",
    },
]


def get_mock_customers() -> list[dict[str, Any]]:
    """Return a fresh copy so one demo run cannot mutate another."""
    return deepcopy(MOCK_CUSTOMERS)
