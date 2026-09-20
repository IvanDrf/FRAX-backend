from typing import Final

RISK_FACTORS: Final = [
    {
        "factor_id": 1,
        "factor_name": "Предыдущие переломы",
        "factor_description": "Наличие переломов увеличивает риск повторных переломов",
        "factor_weight": 1.5,
        "factor_prevalence": 12,
        "factor_category": "binary",
        "image_url": "http://localhost:9000/frax-bucket/brake.jpg",
        "video_url": "http://localhost:9000/frax-bucket/brake.mp4",
        "likes": [2, 3, 5],
        "publication_status": "published",
    },
    {
        "factor_id": 2,
        "factor_name": "Курение",
        "factor_description": "Курение снижает плотность костей",
        "factor_weight": 1.25,
        "factor_prevalence": 22,
        "factor_category": "binary",
        "image_url": "http://localhost:9000/frax-bucket/smoke.jpg",
        "video_url": "http://localhost:9000/frax-bucket/smoke.mp4",
        "likes": [1, 3],
        "publication_status": "published",
    },
    {
        "factor_id": 3,
        "factor_name": "МПК шейки бедра",
        "factor_description": "Минеральная плотность кости шейки бедра",
        "factor_weight": 0.8,
        "factor_prevalence": 8,
        "factor_category": "numeric",
        "image_url": "http://localhost:9000/frax-bucket/osteoporosis.jpg",
        "video_url": "http://localhost:9000/frax-bucket/osteoporosis.mp4",
        "likes": [],
        "publication_status": "draft",
    },
    {
        "factor_id": 4,
        "factor_name": "Ревматоидный артрит",
        "factor_description": "Хроническое воспаление при ревматоидном артрите усиливает костную резорбцию и повышает риск переломов",
        "factor_weight": 1.35,
        "factor_prevalence": 5,
        "factor_category": "binary",
        "image_url": "http://localhost:9000/frax-bucket/arthritis.jpg",
        "video_url": "http://localhost:9000/frax-bucket/arthritis.mp4",
        "likes": [2, 4, 7],
        "publication_status": "published",
    },
    {
        "factor_id": 5,
        "factor_name": "Алкоголь",
        "factor_description": "Употребление более 3 единиц алкоголя в день увеличивает риск переломов. Алкоголь токсичен для остеобластов",
        "factor_weight": 1.15,
        "factor_prevalence": 9,
        "factor_category": "binary",
        "image_url": "http://localhost:9000/frax-bucket/alko.jpg",
        "video_url": "http://localhost:9000/frax-bucket/alko.mp4",
        "likes": [1, 6],
        "publication_status": "published",
    },
]


def is_risk_factor_published(risk_factor: dict) -> bool:
    return risk_factor.get("publication_status", "") == "published"


def is_risk_factor_drafted(risk_factor: dict) -> bool:
    return risk_factor.get("publication_status", "") == "draft"


def is_risk_factor_weight_bigger(risk_factor: dict, risk_factor_weight: float) -> bool:
    return risk_factor.get("factor_weight", 0) > risk_factor_weight
