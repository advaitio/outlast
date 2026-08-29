from outlast.ewaste import find_ewaste_points, load_ewaste_points


def test_nea_ewaste_dataset_loads() -> None:
    assert len(load_ewaste_points()) == 718


def test_ewaste_points_can_be_filtered_by_category_and_location() -> None:
    points = find_ewaste_points("Small household appliances & electronics", "Jurong")

    assert points
    assert all("non-regulated" in point.accepted_items.lower() for point in points)
    assert all("jurong" in f"{point.display_name} {point.address}".lower() for point in points)
