from typing import Final

RISK_FACTORS: Final = [
    {
        "factor_id": 1,
        "factor_name": "Предыдущие переломы",
        "factor_description": "Наличие переломов увеличивает риск повторных переломов",
        "factor_weight": 1.5,
        "factor_category": "binary",
        "image_key": "fracture_history.jpg",
        "video_key": "fracture_explanation.mp4",
        "likes": [2, 3],
        "publication_status": "published",
    },
    {
        "factor_id": 2,
        "factor_name": "Курение",
        "factor_description": "Курение снижает плотность костей",
        "factor_weight": 1.25,
        "factor_category": "binary",
        "image_key": "smoking.jpg",
        "video_key": "smoking_effects.mp4",
        "likes": [1, 3],
        "publication_status": "published",
    },
    {
        "factor_id": 3,
        "factor_name": "МПК шейки бедра",
        "factor_description": "Минеральная плотность кости шейки бедра",
        "factor_weight": 0.8,
        "factor_category": "numeric",
        "image_key": "bmd_measurement.jpg",
        "video_key": "dexa_scan.mp4",
        "likes": [],
        "publication_status": "draft",
    },
]


def is_risk_factor_published(risk_factor: dict) -> bool:
    return risk_factor.get("publication_status", False) is True


def is_risk_factor_weight_bigger(risk_factor: dict, risk_factor_weight: float) -> bool:
    return risk_factor.get("factor_weight", 0) > risk_factor_weight
