import xml.etree.ElementTree as ET
import pandas as pd


def parse_hardware_schedule(xml_path: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Parse a TITAN hardware schedule XML export into three DataFrames.

    Args:
        xml_path: Path to the XML file exported from TITAN/ContractERP.

    Returns:
        A tuple of (project_df, openings_df, hardware_items_df).
        - project_df: Single-row DataFrame with project metadata.
        - openings_df: One row per opening (Assignment_Level_3).
        - hardware_items_df: One row per hardware item assignment
          (Material_List × Assignment combo).
    """
    tree = ET.parse(xml_path)
    root = tree.getroot()

    # --- Project Info ---
    fields = root.find("Fields")
    job_site = fields.find("Job_Site")
    contractor = fields.find("Contractor")
    project_row = {
        "Project_Description": root.attrib.get("Description"),
        "Application": fields.findtext("Application"),
        "Project_ID": fields.findtext("Project_ID"),
        "Submittal_Job_No": fields.findtext("Submittal_Job_No"),
        "Submittal_Assignment_Count": fields.findtext("Submittal_Assignment_Count"),
        "Job_Site_Name": job_site.attrib.get("Name") if job_site is not None else None,
        "Address": job_site.findtext("Address1") if job_site is not None else None,
        "City": job_site.findtext("City") if job_site is not None else None,
        "State": job_site.findtext("State") if job_site is not None else None,
        "Zip": job_site.findtext("Zip") if job_site is not None else None,
        "Contractor": contractor.attrib.get("Name") if contractor is not None else None,
        "Project_Manager": fields.findtext("Project_Manager"),
        "Estimator_Code": fields.findtext("Estimator_Code"),
        "UserID": fields.findtext("UserID"),
    }
    project_df = pd.DataFrame([project_row])

    # --- Opening Info ---
    opening_child_fields = [
        "Assignment_Multiplier", "Building", "Floor", "Location",
        "Location_To", "Interior_Exterior", "Keying", "Heading_No",
        "Hand", "Single_Pair", "Width", "Length", "Door_Thickness",
        "Jamb_Thickness", "Frame_Type", "Door_Type", "Location_From",
    ]

    opening_rows = []
    for assignment in root.find("Assignments"):
        row = {"Opening_Number": assignment.attrib["Code"]}
        for field in opening_child_fields:
            elem = assignment.find(field)
            row[field] = elem.text if elem is not None else None
        opening_rows.append(row)

    openings_df = pd.DataFrame(opening_rows)
    openings_df["Assignment_Multiplier"] = pd.to_numeric(
        openings_df["Assignment_Multiplier"], errors="coerce"
    ).astype("Int64")

    # --- Hardware Items ---
    ml_fields = [
        "Item_Category_Code", "Product_Group_Code", "Submittal_ID",
        "Product_Description", "Quantity", "UOM", "Vendor_No",
        "List_Price", "Vendor_Discount", "Unit_Cost", "Markup_Pct",
        "Unit_Price",
    ]
    numeric_ml_fields = [
        "Total_Project_Quantity", "List_Price", "Vendor_Discount",
        "Unit_Cost", "Markup_Pct", "Unit_Price",
    ]

    hw_rows = []
    for material_list in root.find("Detail"):
        # Fields shared across all assignments of this Material_List
        description5 = material_list.attrib.get("Description")
        mlf = material_list.find("Material_List_Fields")
        shared = {}
        for field in ml_fields:
            elem = mlf.find(field)
            shared[field] = elem.text if elem is not None else None

        # One row per Assignment
        for assign in material_list.find("Assignments"):
            row = {"Product_Code": description5}
            row.update(shared)
            row["Opening_Number"] = assign.attrib["Code"]
            mid = assign.find("Material_ID")
            row["Material_ID"] = mid.text if mid is not None else None
            qp = assign.find("Qty_Per")
            row["Item_Quantity"] = qp.text if qp is not None else None
            pc = assign.find("Phase_Code")
            row["Phase_Code"] = pc.text if pc is not None else None
            hw_rows.append(row)

    hardware_items_df = pd.DataFrame(hw_rows)
    hardware_items_df.rename(columns={
        "Product_Description": "Hardware_Category",
        "Quantity": "Total_Project_Quantity",
    }, inplace=True)
    for col in numeric_ml_fields:
        hardware_items_df[col] = pd.to_numeric(
            hardware_items_df[col], errors="coerce"
        )
    hardware_items_df["Item_Quantity"] = pd.to_numeric(
        hardware_items_df["Item_Quantity"], errors="coerce"
    ).astype("Int64")

    return project_df, openings_df, hardware_items_df


if __name__ == "__main__":
    import sys

    path = sys.argv[1] if len(sys.argv) > 1 else "contracterp-74.xml"
    project, openings, hardware = parse_hardware_schedule(path)

    print("=== Project Info ===")
    print(f"Shape: {project.shape}")
    print(project.to_string(index=False))
    print()
    print("=== Opening Info ===")
    print(f"Shape: {openings.shape}")
    print(openings.head())
    print()
    print("=== Hardware Items ===")
    print(f"Shape: {hardware.shape}")
    print(hardware.head())
