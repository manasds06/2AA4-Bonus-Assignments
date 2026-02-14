import xml.etree.ElementTree as ET
import os
import sys
import re


def parse_xml(filepath):
    tree = ET.parse(filepath)
    root = tree.getroot()

    classes = {}
    inheritance = {}
    fields = {}

    cells = list(root.iter("mxCell"))

    for cell in cells:
        if cell.get("vertex") == "1" and cell.get("value"):
            style = cell.get("style") or ""
            if "edgeLabel" in style:
                continue
            classes[cell.get("id")] = cell.get("value")

    edge_labels = {}
    for cell in cells:
        parent_id = cell.get("parent")
        if cell.get("connectable") == "0" and cell.get("value") and parent_id:
            edge_labels[parent_id] = cell.get("value")

    for cell in cells:
        if cell.get("edge") != "1":
            continue

        source = cell.get("source")
        target = cell.get("target")
        style = cell.get("style") or ""

        if not source or not target:
            continue

        if "endArrow=block" in style and "endFill=0" in style:
            inheritance[source] = target
            continue

        label = cell.get("value") or edge_labels.get(cell.get("id"), "")

        if not label:
            continue

        match = re.match(r"(.+?)\s*\((\w+)\)", label.strip())
        if match:
            field_name = match.group(1).strip()
            cardinality = match.group(2)

            if source not in fields:
                fields[source] = []
            fields[source].append((field_name, target, cardinality))

    return classes, inheritance, fields


def sanitize_name(name):
    parts = name.strip().split()
    return "".join(word.capitalize() for word in parts)


def generate_java(classes, inheritance, fields, output_dir):
    os.makedirs(output_dir, exist_ok=True)

    for class_id, raw_name in classes.items():
        class_name = sanitize_name(raw_name)
        class_fields = fields.get(class_id, [])
        parent_id = inheritance.get(class_id)
        parent_name = sanitize_name(classes[parent_id]) if parent_id and parent_id in classes else None

        needs_list = any(c != "1" for _, _, c in class_fields)

        lines = []

        if needs_list:
            lines.append("import java.util.List;")
            lines.append("")

        header = f"public class {class_name}"
        if parent_name:
            header += f" extends {parent_name}"
        header += " {"

        lines.append(header)

        for field_name, target_id, cardinality in class_fields:
            target_name = sanitize_name(classes[target_id]) if target_id in classes else "Object"
            if cardinality == "1":
                lines.append(f"    private {target_name} {field_name};")
            else:
                lines.append(f"    private List<{target_name}> {field_name};")

        lines.append("}")

        filepath = os.path.join(output_dir, f"{class_name}.java")
        with open(filepath, "w") as f:
            f.write("\n".join(lines) + "\n")
        print(f"Generated {filepath}")


def main():
    if len(sys.argv) != 3:
        print("Usage: python script.py <input.xml> <output-dir>")
        sys.exit(1)

    input_file = sys.argv[1]
    output_dir = sys.argv[2]

    classes, inheritance, fields = parse_xml(input_file)
    generate_java(classes, inheritance, fields, output_dir)


if __name__ == "__main__":
    main()
