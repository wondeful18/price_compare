from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from application.ai_service import AiService
from application.compare_app_service import CompareAppService
from application.dto import MaterialRowDTO
from application.export_app_service import ExportAppService
from application.import_app_service import ImportAppService, ImportAppServiceError
from application.query_builder_service import QueryBuilderService
from application.search_task_service import SearchTaskService
from config.settings import load_settings
from domain.models import CompareResult, MaterialItem
from infra.deepseek_client import DeepSeekClient
from infra.excel_reader import ExcelReader
from infra.excel_writer import ExcelWriter
from infra.http_client import build_mock_http_client
from infra.sqlite_db import SQLiteDB
from providers.jd_provider import JDOfficialProvider
from repositories.cache_repository import CacheRepository
from workers.task_bus import TaskBus
from workers.task_runner import TaskRunner


TABLE_HEADERS = [
    "行号",
    "序号",
    "名称",
    "规格",
    "数量",
    "单位",
    "品牌",
    "投标单价",
    "投标总价",
    "状态",
    "采购价原文",
    "推荐平台",
    "推荐价格",
    "京东最低价",
    "匹配分",
    "AI 备注",
    "任务状态",
    "错误信息",
]


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self._settings = load_settings()
        self._import_service = ImportAppService(ExcelReader())
        self._cache_repository = CacheRepository(SQLiteDB(self._settings.cache_db_path))
        self._export_service = ExportAppService(self._settings, ExcelWriter())
        self._ai_service = AiService(DeepSeekClient(), self._cache_repository)
        self._task_bus = TaskBus()
        self._task_runner = TaskRunner(self._settings.max_workers)
        self._search_service = SearchTaskService(
            provider=JDOfficialProvider(build_mock_http_client()),
            query_builder=QueryBuilderService(),
            compare_service=CompareAppService(self._settings.top_n_offers),
            cache_repository=self._cache_repository,
            ai_service=self._ai_service,
            task_runner=self._task_runner,
            task_bus=self._task_bus,
        )
        self._imported_items: list[MaterialItem] = []
        self._row_index_by_material_id: dict[int, int] = {}
        self._results_by_material_id: dict[int, CompareResult] = {}
        self._init_window()
        self._init_ui()
        self._init_event_timer()

    def closeEvent(self, event) -> None:  # type: ignore[override]
        self._task_runner.shutdown()
        super().closeEvent(event)

    def _init_window(self) -> None:
        self.setWindowTitle(self._settings.window_title)
        self.resize(self._settings.window_width, self._settings.window_height)

    def _init_ui(self) -> None:
        toolbar = QToolBar("工具栏", self)
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        import_button = QPushButton("导入 Excel")
        import_button.clicked.connect(self._on_import_clicked)
        toolbar.addWidget(import_button)

        self._start_button = QPushButton("开始搜索")
        self._start_button.clicked.connect(self._on_start_search_clicked)
        toolbar.addWidget(self._start_button)

        self._stop_button = QPushButton("停止任务")
        self._stop_button.clicked.connect(self._on_stop_search_clicked)
        toolbar.addWidget(self._stop_button)

        self._export_button = QPushButton("导出结果")
        self._export_button.clicked.connect(self._on_export_clicked)
        toolbar.addWidget(self._export_button)

        self._ai_checkbox = QCheckBox("启用 AI")
        self._ai_checkbox.setChecked(self._settings.ai_enabled_default)
        toolbar.addWidget(self._ai_checkbox)

        self._summary_label = QLabel("未导入文件")
        self._summary_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        toolbar.addWidget(self._summary_label)

        main_widget = QWidget(self)
        layout = QVBoxLayout(main_widget)
        layout.setContentsMargins(8, 8, 8, 8)

        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        splitter.setChildrenCollapsible(False)
        layout.addWidget(splitter)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(QLabel("任务区"))

        self._meta_box = QTextEdit()
        self._meta_box.setReadOnly(True)
        left_layout.addWidget(self._meta_box)

        self._event_log = QTextEdit()
        self._event_log.setReadOnly(True)
        left_layout.addWidget(self._event_log)

        self._table = QTableWidget(0, len(TABLE_HEADERS), self)
        self._table.setHorizontalHeaderLabels(TABLE_HEADERS)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.setAlternatingRowColors(True)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

        splitter.addWidget(left_panel)
        splitter.addWidget(self._table)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 4)

        self.setCentralWidget(main_widget)
        self.setStatusBar(QStatusBar(self))

    def _init_event_timer(self) -> None:
        self._event_timer = QTimer(self)
        self._event_timer.setInterval(120)
        self._event_timer.timeout.connect(self._drain_task_events)
        self._event_timer.start()

    def _on_import_clicked(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择 Excel 文件",
            str(Path.cwd()),
            "Excel Files (*.xlsx)",
        )
        if not file_path:
            return

        try:
            result = self._import_service.import_file(file_path)
        except ImportAppServiceError as exc:
            QMessageBox.warning(self, "导入失败", str(exc))
            self.statusBar().showMessage("导入失败", 5000)
            return

        self._imported_items = result.preview.items
        self._results_by_material_id.clear()
        self._summary_label.setText(f"已导入: {Path(file_path).name} | 共 {result.preview.total_rows} 条")
        self._meta_box.setPlainText(
            "\n".join(
                [
                    f"文件: {file_path}",
                    f"工作表: {result.preview.sheet_name}",
                    f"解析条数: {result.preview.total_rows}",
                    f"识别列: {', '.join(result.preview.detected_columns)}",
                    "搜索源: JDOfficialProvider (mock)",
                    f"缓存库: {self._settings.cache_db_path}",
                    f"AI 模式: {'mock' if self._settings.deepseek_mock_enabled else 'real'}",
                ]
            )
        )
        self._populate_table(result.rows)
        self._event_log.clear()
        self.statusBar().showMessage("Excel 导入成功", 5000)

    def _on_start_search_clicked(self) -> None:
        if not self._imported_items:
            QMessageBox.information(self, "无法开始", "请先导入 Excel 文件。")
            return
        ai_enabled = self._ai_checkbox.isChecked()
        self._append_event_log(f"开始批量搜索，AI={'开' if ai_enabled else '关'}")
        session = self._search_service.start_batch(self._imported_items, enable_ai=ai_enabled)
        self.statusBar().showMessage(f"搜索任务已启动，共 {session.total_items} 条", 5000)

    def _on_stop_search_clicked(self) -> None:
        self._search_service.stop_batch()
        self._append_event_log("已请求停止任务")
        self.statusBar().showMessage("已请求停止任务", 5000)

    def _on_export_clicked(self) -> None:
        if not self._imported_items:
            QMessageBox.information(self, "无法导出", "请先导入并搜索数据。")
            return
        export_path = self._export_service.export_results(self._imported_items, self._results_by_material_id)
        self._append_event_log(f"导出完成: {export_path}")
        self.statusBar().showMessage(f"已导出到 {export_path}", 5000)

    def _populate_table(self, rows: list[MaterialRowDTO]) -> None:
        self._table.setRowCount(len(rows))
        self._row_index_by_material_id.clear()
        for row_index, row in enumerate(rows):
            self._row_index_by_material_id[row.row_id] = row_index
            values = [
                str(row.row_id),
                row.serial_no,
                row.name,
                row.spec,
                row.quantity,
                row.unit,
                row.brand,
                row.bid_unit_price,
                row.bid_total_price,
                row.status,
                row.purchase_price_raw,
                row.recommended_platform,
                row.recommended_price,
                row.jd_price,
                row.match_score,
                row.ai_comment,
                row.task_status,
                row.error_message,
            ]
            for column_index, value in enumerate(values):
                self._table.setItem(row_index, column_index, QTableWidgetItem(value))

    def _drain_task_events(self) -> None:
        for event in self._task_bus.drain():
            if event.event_type == "item_started" and event.material_id is not None:
                self._update_row(event.material_id, task_status="搜索中", error_message="")
            elif event.event_type == "item_finished" and event.material_id is not None and event.payload:
                result = event.payload["result"]
                self._results_by_material_id[event.material_id] = result
                self._update_row(
                    event.material_id,
                    recommended_platform=result.best_platform.value if result.best_platform else "",
                    recommended_price=self._fmt_float(result.best_price),
                    jd_price=self._fmt_float(result.jd_price),
                    match_score=self._fmt_float(result.match_score),
                    ai_comment=result.ai_comment or "",
                    task_status=result.search_status.value,
                    error_message="",
                )
                if event.payload.get("retried_with_ai"):
                    self._append_event_log(f"行 {event.material_id} 通过 AI 改写后搜索完成")
                elif event.payload.get("cache_hit"):
                    self._append_event_log(f"行 {event.material_id} 使用缓存")
                elif event.payload.get("ai_used"):
                    self._append_event_log(f"行 {event.material_id} AI 优化后搜索完成")
                else:
                    self._append_event_log(f"行 {event.material_id} 搜索完成")
            elif event.event_type == "item_failed" and event.material_id is not None and event.payload:
                result = event.payload["result"]
                self._results_by_material_id[event.material_id] = result
                self._update_row(
                    event.material_id,
                    task_status=result.search_status.value,
                    error_message=result.error_message or event.error or "",
                )
                self._append_event_log(f"行 {event.material_id} 搜索失败: {result.error_message or event.error or ''}")
            elif event.event_type == "batch_started":
                total = event.payload.get("total") if event.payload else 0
                self._append_event_log(f"批量任务开始，总数 {total}")
            elif event.event_type == "batch_stopping":
                self._append_event_log("批量任务停止中")
            elif event.event_type == "batch_finished":
                self._append_event_log("批量任务完成")
                self.statusBar().showMessage("批量任务完成", 5000)

    def _update_row(self, material_id: int, **changes: str) -> None:
        row_index = self._row_index_by_material_id.get(material_id)
        if row_index is None:
            return
        column_map = {
            "recommended_platform": 11,
            "recommended_price": 12,
            "jd_price": 13,
            "match_score": 14,
            "ai_comment": 15,
            "task_status": 16,
            "error_message": 17,
        }
        for key, value in changes.items():
            if key not in column_map:
                continue
            self._table.setItem(row_index, column_map[key], QTableWidgetItem(value))

    def _append_event_log(self, message: str) -> None:
        self._event_log.append(message)

    @staticmethod
    def _fmt_float(value: float | None) -> str:
        if value is None:
            return ""
        return f"{value:.2f}"
