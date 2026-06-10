import json

from app.repositories.product_repository import ProductRepository


def _write_product(dataset_dir, *, product_id: str, image_path: str) -> None:
    category_dir = dataset_dir / "1_test"
    data_dir = category_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "product_id": product_id,
        "title": f"Test Product {product_id}",
        "brand": "Test Brand",
        "category": "Test Category",
        "sub_category": "Test Subcategory",
        "base_price": 99,
        "image_path": image_path,
        "skus": [],
        "rag_knowledge": {},
    }
    (data_dir / f"{product_id}.json").write_text(json.dumps(payload), encoding="utf-8")


def test_dataset_detail_image_uses_images_android_without_replacing_original(tmp_path):
    dataset_dir = tmp_path / "dataset"
    image_dir = dataset_dir / "1_test" / "images"
    detail_dir = dataset_dir / "1_test" / "images_android"
    image_dir.mkdir(parents=True)
    detail_dir.mkdir(parents=True)
    (image_dir / "test product.jpg").write_bytes(b"original")
    (detail_dir / "test product.jpg").write_bytes(b"detail")
    _write_product(
        dataset_dir,
        product_id="p_test_001",
        image_path="https://host/static/dataset/1_test/images/test%20product.jpg?v=2",
    )

    product = ProductRepository(source_path=tmp_path / "missing.json", dataset_dir=dataset_dir).list_products()[0]

    assert "/images/" in product.image_url
    assert "/images_android/" not in product.image_url
    assert product.detail_image_url is not None
    assert "/images_android/" in product.detail_image_url
    assert product.detail_image_url != product.image_url


def test_dataset_detail_image_is_none_when_android_image_missing(tmp_path):
    dataset_dir = tmp_path / "dataset"
    image_dir = dataset_dir / "1_test" / "images"
    image_dir.mkdir(parents=True)
    (image_dir / "p_test_002.jpg").write_bytes(b"original")
    _write_product(
        dataset_dir,
        product_id="p_test_002",
        image_path="1_test/images/p_test_002.jpg",
    )

    product = ProductRepository(source_path=tmp_path / "missing.json", dataset_dir=dataset_dir).list_products()[0]

    assert "/images/" in product.image_url
    assert product.detail_image_url is None


def test_dataset_original_image_does_not_resolve_to_images_android(tmp_path):
    dataset_dir = tmp_path / "dataset"
    image_dir = dataset_dir / "1_test" / "images"
    detail_dir = dataset_dir / "1_test" / "images_android"
    image_dir.mkdir(parents=True)
    detail_dir.mkdir(parents=True)
    (image_dir / "p_test_003.jpg").write_bytes(b"original")
    (detail_dir / "p_test_003.jpg").write_bytes(b"detail")
    _write_product(
        dataset_dir,
        product_id="p_test_003",
        image_path="1_test/images_android/p_test_003.jpg",
    )

    product = ProductRepository(source_path=tmp_path / "missing.json", dataset_dir=dataset_dir).list_products()[0]

    assert "/images/p_test_003.jpg" in product.image_url
    assert "/images_android/" not in product.image_url
    assert product.detail_image_url is not None
    assert "/images_android/p_test_003.jpg" in product.detail_image_url


def test_dataset_detail_image_can_use_same_stem_common_extension(tmp_path):
    dataset_dir = tmp_path / "dataset"
    image_dir = dataset_dir / "1_test" / "images"
    detail_dir = dataset_dir / "1_test" / "images_android"
    image_dir.mkdir(parents=True)
    detail_dir.mkdir(parents=True)
    (image_dir / "p_test_004.jpg").write_bytes(b"original")
    (detail_dir / "p_test_004.png").write_bytes(b"detail")
    _write_product(
        dataset_dir,
        product_id="p_test_004",
        image_path="1_test/images/p_test_004.jpg",
    )

    product = ProductRepository(source_path=tmp_path / "missing.json", dataset_dir=dataset_dir).list_products()[0]

    assert "/images/p_test_004.jpg" in product.image_url
    assert product.detail_image_url is not None
    assert "/images_android/p_test_004.png" in product.detail_image_url
    assert product.detail_image_url != product.image_url
