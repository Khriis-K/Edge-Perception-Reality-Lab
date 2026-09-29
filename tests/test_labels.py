"""KITTI label parsing: 2D boxes only, and malformed lines reported by line number instead of crashing."""

from backend.labels import Box, parse_labels

# A real-shaped SeeingThroughFog line: 27 fields, visibility flags as True/False words.
CAR = (
    "PassengerCar 0.00 2 -1 421.56 486.74 693.47 599.85 1.35 1.75 3.72 -5.54 1.11 30.04 0.852 0.000 0.000 "
    "2.423 1.00 0.0000000000 0.0000000000 0.9361579423 0.3515797308 True True True False"
)
PEDESTRIAN = "Pedestrian 0.00 0 -1 10.00 20.00 50.50 90.25 1.7 0.6 0.6 1 1 10 0"


def test_reads_the_class_and_the_2d_box():
    boxes, problems = parse_labels(CAR + "\n" + PEDESTRIAN + "\n")

    assert boxes == [
        Box("PassengerCar", 421.56, 486.74, 693.47, 599.85),
        Box("Pedestrian", 10.0, 20.0, 50.5, 90.25),
    ]
    assert problems == []


def test_an_empty_file_has_no_objects():
    assert parse_labels("") == ([], [])


def test_blank_lines_are_skipped():
    boxes, problems = parse_labels("\n" + PEDESTRIAN + "\n\n")

    assert len(boxes) == 1 and problems == []


def test_a_line_with_too_few_fields_is_reported_with_its_line_number():
    boxes, problems = parse_labels(PEDESTRIAN + "\nPassengerCar 0.00 0 not-a-number\n")

    assert [b.label for b in boxes] == ["Pedestrian"]
    assert [p.line for p in problems] == [2]
    assert "line 2" in problems[0].message
    assert "PassengerCar 0.00 0 not-a-number" in problems[0].message  # shows what was read


def test_a_non_numeric_box_is_reported():
    line = PEDESTRIAN.replace("50.50", "wide")

    boxes, problems = parse_labels(line)

    assert boxes == []
    assert [p.line for p in problems] == [1]


def test_an_empty_box_is_reported():
    # Three real SeeingThroughFog lines have a 0 0 0 0 box.
    line = PEDESTRIAN.replace("10.00 20.00 50.50 90.25", "0.00 0.00 0.00 0.00")

    boxes, problems = parse_labels(line)

    assert boxes == []
    assert len(problems) == 1


def test_a_non_finite_box_is_reported():
    boxes, problems = parse_labels(PEDESTRIAN.replace("50.50", "inf"))

    assert boxes == [] and len(problems) == 1
