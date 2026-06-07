import streamlit as st

from database_datasources.components.dialogs import (
    delete_database_datasource_dialog,
    edit_database_datasource_dialog,
)
from database_datasources.services.data_loader_service import load_database_datasource_preview
from database_datasources.services.perimeter_service import (
    build_filter_text,
    build_connection_label,
    build_dataset_summary,
    build_sort_text,
)
from database_datasources.services.state_service import (
    is_database_datasource_open,
    is_database_datasource_preview_visible,
    mark_database_datasource_open,
    set_database_datasource_perimeter_edit_id,
    set_selected_database_datasource_id,
    toggle_database_datasource_preview,
)

DATASET_PERIMETER_EDITOR_PAGE_PATH = "pages/DatasetPerimeterEditor.py"


def render_database_datasources_component(
    datasources: list[dict],
    connections: list[dict],
):
    connection_labels = {
        str(item.get("id")): build_connection_label(item)
        for item in connections
        if item.get("id")
    }

    if not datasources:
        st.info("Nessun dataset configurato.")
        return

    for idx, datasource_item in enumerate(datasources):
        datasource_id = str(datasource_item.get("id") or "").strip()
        summary = build_dataset_summary(datasource_item, connection_labels)
        expanded = is_database_datasource_open(datasource_id) or is_database_datasource_preview_visible(datasource_id)

        with st.expander(summary["description"], expanded=expanded):
            st.write(f"**Database:** {summary['connection_label']}")
            st.write(f"**Schema:** {summary['schema']}")
            st.write(f"**Table/View:** {summary['object_label']}")

            action_cols = st.columns([1, 1, 1, 1], gap="small", vertical_alignment="center")
            with action_cols[0]:
                preview_visible = is_database_datasource_preview_visible(datasource_id)
                if st.button(
                    "Hide preview" if preview_visible else "Preview",
                    key=f"database_datasource_preview_btn_{datasource_id or idx}",
                    icon=":material/visibility:" if not preview_visible else ":material/visibility_off:",
                    type="secondary",
                    use_container_width=True,
                ):
                    is_visible = toggle_database_datasource_preview(datasource_id)
                    set_selected_database_datasource_id(datasource_id)
                    mark_database_datasource_open(datasource_id, is_open=is_visible)
                    st.rerun()
            with action_cols[1]:
                if st.button(
                    "Perimeter",
                    key=f"database_datasource_perimeter_btn_{datasource_id or idx}",
                    icon=":material/filter_alt:",
                    type="secondary",
                    use_container_width=True,
                ):
                    set_database_datasource_perimeter_edit_id(datasource_id)
                    st.switch_page(DATASET_PERIMETER_EDITOR_PAGE_PATH)
            with action_cols[2]:
                if st.button(
                    "Edit",
                    key=f"database_datasource_edit_btn_{datasource_id or idx}",
                    icon=":material/edit:",
                    type="secondary",
                    use_container_width=True,
                ):
                    set_selected_database_datasource_id(datasource_id)
                    mark_database_datasource_open(datasource_id, is_open=True)
                    edit_database_datasource_dialog(datasource_item)
            with action_cols[3]:
                if st.button(
                    "Delete",
                    key=f"database_datasource_delete_btn_{datasource_id or idx}",
                    icon=":material/delete:",
                    help="Delete dataset",
                    type="secondary",
                    use_container_width=True,
                ):
                    set_selected_database_datasource_id(datasource_id)
                    mark_database_datasource_open(datasource_id, is_open=True)
                    delete_database_datasource_dialog(datasource_item)

            if is_database_datasource_preview_visible(datasource_id):
                perimeter = datasource_item.get("perimeter") if isinstance(datasource_item.get("perimeter"), dict) else None
                filter_text = build_filter_text(perimeter)
                sort_text = build_sort_text(perimeter)
                if filter_text:
                    st.caption(f"Filters: {filter_text}")
                if sort_text:
                    st.caption(f"Sort: {sort_text}")
                preview_payload = load_database_datasource_preview(datasource_id, force=False)
                if isinstance(preview_payload, dict) and preview_payload.get("error"):
                    st.error(f"Errore preview: {preview_payload.get('error')}")
                else:
                    rows = preview_payload.get("rows") if isinstance(preview_payload, dict) else []
                    if rows:
                        st.dataframe(rows, use_container_width=True, height=320)
                    else:
                        st.info("Nessun dato disponibile per la preview.")
