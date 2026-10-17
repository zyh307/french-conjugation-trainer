# -*- coding: utf-8 -*-
# main_gui.py - 法语变位练习器界面

import sys
import os
import random
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QKeySequence

from conjugaison_core import *


def create_styled_button(text, callback, color="#3498db", height=40, font_size=13):
    btn = QPushButton(text)
    btn.setFont(QFont("Arial", font_size, QFont.Bold))
    btn.setMinimumHeight(height)
    btn.setCursor(Qt.PointingHandCursor)
    btn.setStyleSheet(f"""
        QPushButton {{
            background: {color};
            color: white;
            border-radius: 8px;
            padding: 6px 12px;
            border: none;
        }}
        QPushButton:hover {{ opacity: 0.85; }}
        QPushButton:pressed {{ opacity: 0.7; }}
    """)
    btn.clicked.connect(callback)
    return btn


def create_empty_message(text="暂无内容"):
    widget = QWidget()
    layout = QHBoxLayout()
    layout.setContentsMargins(10, 5, 10, 5)
    label = QLabel(f"📖 {text}")
    label.setFont(QFont("Arial", 14))
    label.setStyleSheet("color: #95a5a6; padding: 20px;")
    label.setAlignment(Qt.AlignCenter)
    layout.addWidget(label)
    widget.setLayout(layout)
    return widget


def add_empty_item(list_widget, text="暂无内容"):
    widget = create_empty_message(text)
    item_widget = QListWidgetItem()
    item_widget.setSizeHint(widget.sizeHint())
    list_widget.addItem(item_widget)
    list_widget.setItemWidget(item_widget, widget)


class SearchResultWindow(QDialog):
    def __init__(self, verbe, data, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"🔍 搜索结果 - {verbe}")
        self.setMinimumSize(700, 500)
        self.setModal(True)
        self.setStyleSheet("background: #f5f6fa;")
        
        layout = QVBoxLayout()
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)
        self.setLayout(layout)
        
        title = QLabel(f"📖 <b>{verbe}</b> 变位表")
        title.setFont(QFont("Arial", 20, QFont.Bold))
        title.setStyleSheet("color: #2c3e50; padding: 8px;")
        layout.addWidget(title)
        
        self.table = QTableWidget()
        self.table.setFont(QFont("Arial", 13))
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("""
            QTableWidget {
                background: white;
                border-radius: 12px;
                border: none;
                gridline-color: #ecf0f1;
            }
            QTableWidget::item {
                padding: 8px 12px;
            }
            QTableWidget::item:selected {
                background: #e8f0fe;
            }
            QHeaderView::section {
                background: #2c3e50;
                color: white;
                padding: 8px 12px;
                font-weight: bold;
                border: none;
            }
        """)
        layout.addWidget(self.table)
        
        close_btn = create_styled_button("关闭", self.accept, "#e74c3c", 40, 14)
        layout.addWidget(close_btn)
        
        self.populate_table(data)
    
    def populate_table(self, data):
        personnes = ["je", "tu", "il", "nous", "vous", "ils"]
        display_pers = ["je", "tu", "il/elle", "nous", "vous", "ils/elles"]
        
        levels = list(data.keys())
        levels.sort(key=lambda x: ["必会", "常用", "生僻"].index(x) if x in ["必会", "常用", "生僻"] else 999)
        
        all_temps = set()
        for level in levels:
            all_temps.update(data[level].keys())
        all_temps = sorted(all_temps, key=lambda x: ["现在时", "复合过去时", "未完成过去时"].index(x) if x in ["现在时", "复合过去时", "未完成过去时"] else 999)
        
        self.table.setRowCount(6)
        self.table.setColumnCount(len(levels) * len(all_temps))
        
        headers = []
        for level in levels:
            for temps in all_temps:
                if temps in data[level]:
                    headers.append(f"{level}\n{temps}")
                else:
                    headers.append("")
        self.table.setHorizontalHeaderLabels(headers)
        
        for i, p in enumerate(display_pers):
            self.table.setVerticalHeaderItem(i, QTableWidgetItem(p))
        
        for i, p in enumerate(personnes):
            for j, level in enumerate(levels):
                for k, temps in enumerate(all_temps):
                    col = j * len(all_temps) + k
                    if col >= self.table.columnCount():
                        continue
                    if temps in data[level] and p in data[level][temps]:
                        item = QTableWidgetItem(data[level][temps][p])
                        item.setTextAlignment(Qt.AlignCenter)
                        self.table.setItem(i, col, item)
                    else:
                        item = QTableWidgetItem("—")
                        item.setTextAlignment(Qt.AlignCenter)
                        item.setForeground(QColor("#bdc3c7"))
                        self.table.setItem(i, col, item)
        
        self.table.resizeColumnsToContents()
        self.table.resizeRowsToContents()
        
        for col in range(self.table.columnCount()):
            self.table.setColumnWidth(col, max(self.table.columnWidth(col), 100))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🇫🇷 法语变位练习器")
        self.setGeometry(100, 100, 900, 750)
        self.setMinimumSize(800, 650)

        self.data_dict, self.data_list = {}, []
        self.stats = charger_statistiques()
        self.settings = charger_settings()

        self.current_level = None
        self.current_temps = None
        self.search_selected_temps = "现在时"

        self.learn_session = None
        self.review_session = None
        self.current_page = None
        self._reverse_data = None
        self._selected_reverse = None

        self.learn_groups = []
        self.learn_group_index = 0
        self.learn_group_entries = []
        self.is_in_learn = False
        self.is_in_review = False
        self.resume_mode = False

        self.setup_ui()
        self.switch_page("home")
        self.update_main_status()
        QTimer.singleShot(500, self.auto_resume_progress)
        self.setup_shortcuts()

    def start_learning(self):
        """开始学习 - 初始化学习会话"""
        try:
            if self.current_level is None or self.current_temps is None:
                QMessageBox.warning(self, "提示", "请先选择等级和时态！")
                return
            
            # 检查是否有未完成的进度
            progress = get_progress(self.current_level, self.current_temps)
            if progress and progress.get('queue') and len(progress.get('queue', [])) > 0:
                reply = QMessageBox.question(
                    self, "继续学习",
                    f"检测到「{self.current_level} - {self.current_temps}」有未完成的学习进度，是否继续？\n\n"
                    f"选择「是」继续上次学习\n"
                    f"选择「否」重新开始",
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply == QMessageBox.Yes:
                    self.resume_mode = True
                    self._resume_learning(progress)
                    return
                else:
                    clear_progress(self.current_level, self.current_temps)
            
            data_dict, _ = charger_wordlist_cached(self.current_level, self.current_temps)
            if not data_dict:
                QMessageBox.warning(self, "错误", f"未找到 {self.current_level} - {self.current_temps} 的数据！")
                return
            
            count = self.learn_count_spin.value()
            
            self.learn_session = LearnSession(
                data_dict, 
                self.settings, 
                self.current_level, 
                self.current_temps,
                count
            )
            
            if self.learn_session.is_empty():
                QMessageBox.information(self, "提示", "该内容已全部掌握！🎉")
                return
            
            self.hide_nav()
            self.is_in_learn = True
            self.resume_mode = False
            self.learn_stack.setCurrentIndex(1)
            self.learn_group_index = 0
            self.learn_groups = self.learn_session.groups
            QTimer.singleShot(100, self.show_current_round)
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"开始学习失败：{str(e)}")
            print(f"start_learning 错误：{e}")

    def _resume_learning(self, progress):
        """恢复学习进度"""
        try:
            data_dict, _ = charger_wordlist_cached(self.current_level, self.current_temps)
            if not data_dict:
                QMessageBox.warning(self, "错误", f"未找到 {self.current_level} - {self.current_temps} 的数据！")
                return
            
            count = self.learn_count_spin.value()
            self.learn_session = LearnSession(
                data_dict,
                self.settings,
                self.current_level,
                self.current_temps,
                count
            )
            
            self.learn_session.queue = progress.get('queue', [])
            self.learn_session.index = progress.get('index', 0)
            self.learn_groups = progress.get('groups', [self.learn_session.queue])
            self.learn_group_index = progress.get('group_index', 0)
            
            if not self.learn_session.queue:
                QMessageBox.information(self, "提示", "该内容已全部掌握！🎉")
                return
            
            self.hide_nav()
            self.is_in_learn = True
            self.learn_stack.setCurrentIndex(1)
            QTimer.singleShot(100, self.show_current_round)
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"恢复学习失败：{str(e)}")
            print(f"_resume_learning 错误：{e}")

    def show_learn_select(self):
        self.learn_stack.setCurrentIndex(0)
        self.show_nav()

    def back_to_learn_select(self):
        self.learn_stack.setCurrentIndex(0)
        self.show_nav()
        self.update_progress_info()

    def setup_shortcuts(self):
        QShortcut(QKeySequence("Esc"), self, self.go_home)
        QShortcut(QKeySequence("Ctrl+R"), self, self.reset_current_progress)

    def go_home(self):
        self.switch_page("home")

    def reset_current_progress(self):
        if self.current_level and self.current_temps:
            self.reset_progress()

    def setup_ui(self):
        central = QWidget()
        central.setStyleSheet("background: #f5f6fa;")
        self.setCentralWidget(central)
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        central.setLayout(main_layout)

        self.nav_widget = QWidget()
        self.nav_widget.setMinimumWidth(150)
        self.nav_widget.setMaximumWidth(220)
        self.nav_widget.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2c3e50, stop:1 #1a252f);
                border-top-right-radius: 20px;
                border-bottom-right-radius: 20px;
            }
            QPushButton {
                background: transparent;
                color: #b0bec5;
                border: none;
                padding: 14px 20px;
                font-size: 15px;
                text-align: left;
                font-weight: bold;
                border-radius: 10px;
                margin: 2px 10px;
            }
            QPushButton:hover {
                background: rgba(255,255,255,0.08);
                color: #ecf0f1;
            }
            QPushButton:checked {
                background: rgba(52,152,219,0.25);
                color: #ecf0f1;
                border-left: 3px solid #3498db;
            }
        """)

        nav_layout = QVBoxLayout()
        nav_layout.setSpacing(2)
        nav_layout.setContentsMargins(0, 25, 0, 20)
        self.nav_widget.setLayout(nav_layout)

        title_label = QLabel("🇫🇷 法语变位")
        title_label.setStyleSheet("""
            color: #ecf0f1;
            font-size: 22px;
            font-weight: bold;
            padding: 8px 20px 20px 20px;
            border-bottom: 1px solid rgba(255,255,255,0.06);
        """)
        nav_layout.addWidget(title_label)
        nav_layout.addSpacing(15)

        nav_buttons = [
            ("🏠 主页", "home"),
            ("📚 学习", "learn"),
            ("🔄 复习", "review"),
            ("📕 错题本", "errors"),
            ("📖 掌握库", "mastered"),
            ("🔍 查找", "search"),
            ("⚙️ 设置", "settings")
        ]

        self.nav_buttons = {}
        for text, page_id in nav_buttons:
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, p=page_id: self.switch_page(p))
            nav_layout.addWidget(btn)
            self.nav_buttons[page_id] = btn

        nav_layout.addStretch()

        exit_btn = QPushButton("🚪 退出")
        exit_btn.setStyleSheet("""
            QPushButton {
                background: rgba(231,76,60,0.15);
                color: #e74c3c;
                border-radius: 10px;
                padding: 12px;
                font-size: 14px;
                font-weight: bold;
                margin: 10px 15px;
            }
            QPushButton:hover {
                background: rgba(231,76,60,0.3);
            }
        """)
        exit_btn.setCursor(Qt.PointingHandCursor)
        exit_btn.clicked.connect(self.close_app)
        nav_layout.addWidget(exit_btn)

        main_layout.addWidget(self.nav_widget)

        self.content_container = QWidget()
        self.content_container.setStyleSheet("""
            QWidget {
                background: #f5f6fa;
                border-top-right-radius: 20px;
                border-bottom-right-radius: 20px;
            }
        """)
        self.content_layout = QVBoxLayout()
        self.content_layout.setContentsMargins(25, 25, 25, 25)
        self.content_layout.setSpacing(12)
        self.content_container.setLayout(self.content_layout)
        main_layout.addWidget(self.content_container)

    def hide_nav(self):
        self.nav_widget.setVisible(False)

    def show_nav(self):
        self.nav_widget.setVisible(True)

    def auto_resume_progress(self):
        progress = charger_progress()
        if progress:
            for level in progress:
                for temps in progress[level]:
                    data = progress[level][temps]
                    if data.get('queue') and len(data.get('queue', [])) > 0:
                        self.resume_mode = True
                        self.current_level = level
                        self.current_temps = temps
                        self.switch_page("learn")
                        return

    def safe_save_progress(self):
        try:
            if self.is_in_learn and self.learn_session is not None:
                progress_data = {
                    "index": self.learn_session.index,
                    "queue": self.learn_session.queue,
                    "group_index": self.learn_group_index,
                    "groups": self.learn_groups
                }
                set_progress(self.current_level, self.current_temps, progress_data)
                return True
        except Exception as e:
            print(f"保存进度失败：{e}")
        return False

    def closeEvent(self, event):
        if self.is_in_learn and self.learn_session is not None:
            if self.learn_session.has_next():
                self.safe_save_progress()
        if self.is_in_review and self.review_session is not None:
            if self.review_session.has_next():
                review_progress = {
                    "index": self.review_session.index,
                    "sub_index": self.review_session.sub_index,
                    "keys": self.review_session.keys
                }
                set_review_progress(review_progress)
        event.accept()

    def switch_page(self, page_id):
        if page_id != "learn" and self.is_in_learn:
            self.safe_save_progress()
            self.is_in_learn = False

        for pid, btn in self.nav_buttons.items():
            btn.setChecked(pid == page_id)

        self.clear_container()

        if page_id == "home":
            self.current_page = self.create_home_page()
            self.show_nav()
        elif page_id == "learn":
            self.current_page = self.create_learn_page()
            self.show_learn_select()
        elif page_id == "review":
            self.current_page = self.create_review_page()
            self.prepare_review()
        elif page_id == "errors":
            self.current_page = self.create_errors_page()
            self.refresh_errors_list()
            self.show_nav()
        elif page_id == "mastered":
            self.current_page = self.create_mastered_page()
            self.refresh_mastered_list()
            self.show_nav()
        elif page_id == "search":
            self.current_page = self.create_search_page()
            self.show_nav()
        elif page_id == "settings":
            self.current_page = self.create_settings_page()
            self.refresh_settings_values()
            self.show_nav()

        if self.current_page:
            self.content_layout.addWidget(self.current_page)

    def clear_container(self):
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.current_page = None

    # ================================================================
    #                         主页面
    # ================================================================

    def create_home_page(self):
        page = QWidget()
        page.setStyleSheet("background: #f5f6fa;")
        layout = QVBoxLayout()
        page.setLayout(layout)
        layout.setSpacing(16)
        layout.setContentsMargins(10, 10, 10, 10)

        welcome = QLabel("🇫🇷 欢迎回来！")
        welcome.setAlignment(Qt.AlignCenter)
        welcome.setFont(QFont("Arial", 24, QFont.Bold))
        welcome.setStyleSheet("color: #2c3e50; padding: 5px;")
        layout.addWidget(welcome)

        # 复习一览
        review_card = QGroupBox("🔄 需要复习的单词")
        review_card.setFont(QFont("Arial", 13, QFont.Bold))
        review_card.setStyleSheet("""
            QGroupBox {
                background: white;
                border-radius: 14px;
                border: none;
                padding: 8px 12px 12px 12px;
                margin-top: 6px;
                font-weight: bold;
                color: #2c3e50;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                padding: 0 8px;
                color: #2c3e50;
            }
        """)
        review_layout = QVBoxLayout()
        review_layout.setSpacing(4)
        self.review_word_list = QLabel("暂无需要复习的单词")
        self.review_word_list.setFont(QFont("Arial", 12))
        self.review_word_list.setStyleSheet("color: #34495e; padding: 5px;")
        self.review_word_list.setWordWrap(True)
        review_layout.addWidget(self.review_word_list)
        
        self.start_review_btn = create_styled_button("▶ 开始复习", self.go_to_review, "#e67e22", 40, 14)
        self.start_review_btn.setVisible(False)
        review_layout.addWidget(self.start_review_btn)
        
        review_card.setLayout(review_layout)
        layout.addWidget(review_card)

        plan_card = QGroupBox("📋 今日计划")
        plan_card.setFont(QFont("Arial", 13, QFont.Bold))
        plan_card.setStyleSheet("""
            QGroupBox {
                background: white;
                border-radius: 14px;
                border: none;
                padding: 8px 12px 12px 12px;
                margin-top: 6px;
                font-weight: bold;
                color: #2c3e50;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                padding: 0 8px;
                color: #2c3e50;
            }
        """)
        plan_layout = QVBoxLayout()
        plan_layout.setSpacing(4)
        self.plan_status_label = QLabel("")
        self.plan_status_label.setFont(QFont("Arial", 12))
        self.plan_status_label.setStyleSheet("color: #34495e; padding: 2px;")
        plan_layout.addWidget(self.plan_status_label)
        plan_card.setLayout(plan_layout)
        layout.addWidget(plan_card)

        self.home_stats = QLabel("")
        self.home_stats.setAlignment(Qt.AlignCenter)
        self.home_stats.setFont(QFont("Arial", 13))
        self.home_stats.setStyleSheet("""
            background: white;
            padding: 18px;
            border-radius: 14px;
            border: none;
            color: #2c3e50;
            font-weight: bold;
        """)
        layout.addWidget(self.home_stats)

        layout.addStretch()
        self.update_main_status()
        return page

    def go_to_review(self):
        """跳转到复习页面"""
        self.switch_page("review")

    def update_main_status(self):
        try:
            total = self.stats.get('total', 0)
            correct = self.stats.get('correct', 0)
            rate = calculer_taux_reussite(self.stats)
            maitrises = compter_maitrises()
            erreurs = compter_erreurs()
            self.home_stats.setText(
                f"📊 总练习：{total} 题\n"
                f"✅ 正确率：{rate:.0f}%\n"
                f"📖 已掌握：{maitrises} 个\n"
                f"📕 错题：{erreurs} 个"
            )

            review_list = get_review_list()
            if review_list:
                groups = {}
                for item in review_list:
                    key = (item['verbe'], item['temps'])
                    if key not in groups:
                        groups[key] = []
                    groups[key].append(item['personne'])
                
                lines = []
                for (v, t), personnes in groups.items():
                    # 获取学习天数
                    days = 0
                    for p in personnes:
                        m = next((x for x in charger_maitrises() if x['verbe'] == v and x['temps'] == t and x['personne'] == p), None)
                        if m:
                            days = max(days, m.get('days', 0))
                    pers_display = []
                    for p in personnes:
                        if p == "il":
                            pers_display.append("il/elle")
                        elif p == "ils":
                            pers_display.append("ils/elles")
                        else:
                            pers_display.append(p)
                    lines.append(f"• {v} - {t}（{', '.join(pers_display)}）学习{days}天")
                
                self.review_word_list.setText("\n".join(lines))
                self.review_word_list.setStyleSheet("color: #e67e22; padding: 5px; font-weight: bold;")
                self.start_review_btn.setVisible(True)
            else:
                self.review_word_list.setText("✅ 暂无需要复习的单词")
                self.review_word_list.setStyleSheet("color: #2ecc71; padding: 5px; font-weight: bold;")
                self.start_review_btn.setVisible(False)

        except Exception as e:
            print(f"更新状态失败：{e}")

    # ================================================================
    #                         学习页面
    # ================================================================

    def create_learn_page(self):
        page = QWidget()
        page.setStyleSheet("background: #f5f6fa;")
        layout = QVBoxLayout()
        page.setLayout(layout)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.learn_stack = QStackedWidget()
        layout.addWidget(self.learn_stack)

        self.learn_select_widget = self.create_learn_select()
        self.learn_stack.addWidget(self.learn_select_widget)

        self.learn_practice_widget = self.create_learn_practice()
        self.learn_stack.addWidget(self.learn_practice_widget)

        self.learn_stack.setCurrentIndex(0)
        return page

    def create_learn_select(self):
        page = QWidget()
        page.setStyleSheet("background: #f5f6fa;")
        layout = QVBoxLayout()
        page.setLayout(layout)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)

        title = QLabel("📚 选择学习内容")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont("Arial", 20, QFont.Bold))
        title.setStyleSheet("color: #2c3e50;")
        layout.addWidget(title)

        layout.addWidget(QLabel("选择等级："))
        level_layout = QHBoxLayout()
        level_layout.setSpacing(10)
        self.level_buttons = []
        levels = get_available_levels()
        if not levels:
            label = QLabel("⚠️ 未找到任何单词本，请检查 wordlists 文件夹")
            label.setStyleSheet("color: #e74c3c; padding: 10px;")
            level_layout.addWidget(label)
        else:
            for level in levels:
                btn = QPushButton(level)
                btn.setCheckable(True)
                btn.setFont(QFont("Arial", 14))
                btn.setMinimumHeight(40)
                btn.setStyleSheet("""
                    QPushButton {
                        background: white;
                        border: 2px solid #dcdde1;
                        border-radius: 8px;
                        padding: 6px 16px;
                    }
                    QPushButton:checked {
                        border: 2px solid #3498db;
                        background: #e8f0fe;
                    }
                    QPushButton:hover {
                        border: 2px solid #3498db;
                    }
                """)
                btn.clicked.connect(lambda checked, l=level: self.select_level(l))
                level_layout.addWidget(btn)
                self.level_buttons.append(btn)
        level_layout.addStretch()
        layout.addLayout(level_layout)

        layout.addWidget(QLabel("选择时态："))
        temps_layout = QHBoxLayout()
        temps_layout.setSpacing(10)
        self.temps_buttons = []
        self.temps_layout = temps_layout
        layout.addLayout(temps_layout)

        count_layout = QHBoxLayout()
        count_layout.setSpacing(10)
        count_label = QLabel("📊 本次学习数量：")
        count_label.setFont(QFont("Arial", 13))
        count_layout.addWidget(count_label)

        self.learn_count_spin = QSpinBox()
        self.learn_count_spin.setRange(1, 100)
        self.learn_count_spin.setValue(9)
        self.learn_count_spin.setFont(QFont("Arial", 14))
        self.learn_count_spin.setMinimumHeight(35)
        self.learn_count_spin.setStyleSheet("""
            QSpinBox {
                border: 2px solid #dcdde1;
                border-radius: 8px;
                padding: 2px 8px;
                background: white;
            }
            QSpinBox:focus {
                border: 2px solid #3498db;
            }
        """)
        count_layout.addWidget(self.learn_count_spin)

        count_hint = QLabel("（每3个一组判断）")
        count_hint.setFont(QFont("Arial", 11))
        count_hint.setStyleSheet("color: #95a5a6;")
        count_layout.addWidget(count_hint)
        count_layout.addStretch()
        layout.addLayout(count_layout)

        self.progress_info_label = QLabel("请先选择等级和时态")
        self.progress_info_label.setAlignment(Qt.AlignCenter)
        self.progress_info_label.setFont(QFont("Arial", 12))
        self.progress_info_label.setStyleSheet("color: #7f8c8d; padding: 10px;")
        layout.addWidget(self.progress_info_label)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)
        self.start_btn = create_styled_button("▶ 开始学习", self.start_learning, "#2ecc71", 50, 16)
        self.start_btn.setEnabled(False)
        btn_layout.addWidget(self.start_btn)

        self.reset_btn = create_styled_button("🔄 重新开始", self.reset_progress, "#e67e22", 50, 16)
        self.reset_btn.setEnabled(False)
        btn_layout.addWidget(self.reset_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        layout.addStretch()
        return page

    def select_level(self, level):
        for btn in self.level_buttons:
            if btn.text() == level:
                btn.setChecked(True)
            else:
                btn.setChecked(False)
        self.current_level = level
        self.update_temps_buttons()
        self.update_progress_info()

    def update_temps_buttons(self):
        while self.temps_layout.count():
            item = self.temps_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.temps_buttons.clear()

        if self.current_level is None:
            return

        all_temps = ["现在时", "复合过去时", "未完成过去时"]
        path = os.path.join(BASE_DIR, "wordlists", self.current_level)
        existing = []
        if os.path.exists(path):
            for f in os.listdir(path):
                if f.endswith(".csv"):
                    existing.append(f.replace(".csv", ""))

        for temps in all_temps:
            btn = QPushButton(temps)
            btn.setCheckable(True)
            btn.setFont(QFont("Arial", 14))
            btn.setMinimumHeight(40)
            if temps in existing:
                btn.setEnabled(True)
                btn.setStyleSheet("""
                    QPushButton {
                        background: white;
                        border: 2px solid #dcdde1;
                        border-radius: 8px;
                        padding: 6px 16px;
                    }
                    QPushButton:checked {
                        border: 2px solid #3498db;
                        background: #e8f0fe;
                    }
                    QPushButton:hover {
                        border: 2px solid #3498db;
                    }
                """)
                btn.clicked.connect(lambda checked, t=temps: self.select_temps(t))
            else:
                btn.setEnabled(False)
                btn.setStyleSheet("""
                    QPushButton {
                        background: #ecf0f1;
                        color: #bdc3c7;
                        border: 2px solid #dcdde1;
                        border-radius: 8px;
                        padding: 6px 16px;
                    }
                """)
            self.temps_layout.addWidget(btn)
            self.temps_buttons.append(btn)
        
        self.temps_layout.addStretch()

    def select_temps(self, temps):
        for btn in self.temps_buttons:
            if btn.text() == temps:
                btn.setChecked(True)
            else:
                btn.setChecked(False)
        self.current_temps = temps
        self.update_progress_info()

    def update_progress_info(self):
        try:
            if self.current_level is None or self.current_temps is None:
                self.progress_info_label.setText("请先选择等级和时态")
                self.start_btn.setEnabled(False)
                self.reset_btn.setEnabled(False)
                return

            total, mastered = get_wordlist_stats(self.current_level, self.current_temps)
            progress = get_progress(self.current_level, self.current_temps)
            index = progress.get('index', 0)
            queue_len = len(progress.get('queue', []))

            if queue_len > 0:
                remaining = queue_len - index
                self.progress_info_label.setText(
                    f"📊 {self.current_level} - {self.current_temps}\n"
                    f"已掌握：{mastered} / {total} 类\n"
                    f"上次进度：{index} / {queue_len}\n"
                    f"剩余：{remaining} 个"
                )
            else:
                wl_dict, wl_list = charger_wordlist(self.current_level, self.current_temps)
                if wl_list:
                    classes = set()
                    for verbe, t, personne in wl_list:
                        classes.add((verbe, t))
                    total_classes = len(classes)
                    self.progress_info_label.setText(
                        f"📊 {self.current_level} - {self.current_temps}\n"
                        f"已掌握：{mastered} / {total} 类\n"
                        f"总共：{total_classes} 类\n"
                        f"💡 点击「开始学习」开始"
                    )
                else:
                    self.progress_info_label.setText(
                        f"⚠️ 未找到 {self.current_level} - {self.current_temps} 的数据文件"
                    )

            self.start_btn.setEnabled(True)
            self.reset_btn.setEnabled(True)
        except Exception as e:
            print(f"更新进度信息失败：{e}")

    def reset_progress(self):
        if self.current_level is None or self.current_temps is None:
            return

        reply = QMessageBox.question(
            self, "确认重置",
            f"确定要重置「{self.current_level} - {self.current_temps}」的学习进度吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            clear_progress(self.current_level, self.current_temps)
            self.update_progress_info()
            QMessageBox.information(self, "成功", "进度已重置！")

    # ================================================================
    #                         做题界面
    # ================================================================

    def create_learn_practice(self):
        page = QWidget()
        page.setStyleSheet("background: #f5f6fa;")
        layout = QVBoxLayout()
        page.setLayout(layout)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)

        top_layout = QHBoxLayout()
        back_btn = QPushButton("⬅️ 返回")
        back_btn.setFont(QFont("Arial", 12, QFont.Bold))
        back_btn.setMinimumHeight(35)
        back_btn.setFixedWidth(100)
        back_btn.setStyleSheet("""
            QPushButton {
                background: #e74c3c;
                color: white;
                border-radius: 8px;
                border: none;
                padding: 4px 12px;
            }
            QPushButton:hover { background: #c0392b; }
        """)
        back_btn.clicked.connect(self.back_from_learn)
        top_layout.addWidget(back_btn)

        top_layout.addStretch()
        self.learn_title = QLabel("📚 学习")
        self.learn_title.setFont(QFont("Arial", 16, QFont.Bold))
        self.learn_title.setStyleSheet("color: #2c3e50;")
        top_layout.addWidget(self.learn_title)
        top_layout.addStretch()
        layout.addLayout(top_layout)

        self.learn_progress_label = QLabel("进度：0 / 0")
        self.learn_progress_label.setAlignment(Qt.AlignCenter)
        self.learn_progress_label.setFont(QFont("Arial", 12))
        self.learn_progress_label.setStyleSheet("color: #7f8c8d; padding: 2px;")
        layout.addWidget(self.learn_progress_label)

        self.learn_round_label = QLabel("")
        self.learn_round_label.setAlignment(Qt.AlignCenter)
        self.learn_round_label.setFont(QFont("Arial", 14, QFont.Bold))
        self.learn_round_label.setStyleSheet("color: #3498db; padding: 2px;")
        layout.addWidget(self.learn_round_label)

        self.learn_question_label = QLabel("准备开始")
        self.learn_question_label.setAlignment(Qt.AlignCenter)
        self.learn_question_label.setFont(QFont("Arial", 18, QFont.Bold))
        self.learn_question_label.setMinimumHeight(60)
        self.learn_question_label.setStyleSheet("""
            background: white;
            padding: 16px;
            border-radius: 14px;
            border: none;
            color: #2c3e50;
        """)
        layout.addWidget(self.learn_question_label)

        self.learn_hint_label = QLabel("")
        self.learn_hint_label.setAlignment(Qt.AlignCenter)
        self.learn_hint_label.setFont(QFont("Arial", 13))
        self.learn_hint_label.setStyleSheet("color: #2ecc71; padding: 2px; font-weight: bold;")
        layout.addWidget(self.learn_hint_label)

        self.learn_judge_grid = QGridLayout()
        self.learn_judge_grid.setSpacing(8)
        layout.addLayout(self.learn_judge_grid)

        input_layout = QHBoxLayout()
        input_layout.setSpacing(10)
        self.learn_input = QLineEdit()
        self.learn_input.setPlaceholderText("✏️ 输入答案...")
        self.learn_input.setFont(QFont("Arial", 16))
        self.learn_input.setMinimumHeight(42)
        self.learn_input.setStyleSheet("""
            QLineEdit {
                border: 2px solid #dcdde1;
                border-radius: 10px;
                padding: 4px 12px;
                background: white;
            }
            QLineEdit:focus {
                border: 2px solid #3498db;
            }
        """)
        self.learn_input.returnPressed.connect(self.submit_learn_answer)
        input_layout.addWidget(self.learn_input)

        self.learn_submit_btn = QPushButton("✅ 提交")
        self.learn_submit_btn.setFont(QFont("Arial", 13, QFont.Bold))
        self.learn_submit_btn.setMinimumHeight(42)
        self.learn_submit_btn.setFixedWidth(90)
        self.learn_submit_btn.setCursor(Qt.PointingHandCursor)
        self.learn_submit_btn.setStyleSheet("""
            QPushButton {
                background: #3498db;
                color: white;
                border-radius: 10px;
                border: none;
                padding: 4px 10px;
            }
            QPushButton:hover { background: #2980b9; }
        """)
        self.learn_submit_btn.clicked.connect(self.submit_learn_answer)
        input_layout.addWidget(self.learn_submit_btn)
        layout.addLayout(input_layout)

        self.judge_layout = QHBoxLayout()
        self.judge_layout.setSpacing(8)
        self.judge_btn_1 = create_styled_button("✅ 已掌握 [1]", lambda: self.process_judge(1), "#2ecc71", 40, 13)
        self.judge_btn_2 = create_styled_button("🤔 不确定 [2]", lambda: self.process_judge(2), "#f39c12", 40, 13)
        self.judge_btn_3 = create_styled_button("❌ 完全不懂 [3]", lambda: self.process_judge(3), "#e74c3c", 40, 13)
        self.judge_layout.addWidget(self.judge_btn_1)
        self.judge_layout.addWidget(self.judge_btn_2)
        self.judge_layout.addWidget(self.judge_btn_3)
        layout.addLayout(self.judge_layout)

        self.choice_layout = QVBoxLayout()
        self.choice_buttons = []
        layout.addLayout(self.choice_layout)

        self.choice_confirm_layout = QHBoxLayout()
        self.choice_confirm_layout.addStretch()
        self.choice_confirm_btn = create_styled_button("✅ 确定", self.confirm_choice, "#2ecc71", 40, 14)
        self.choice_confirm_btn.setVisible(False)
        self.choice_confirm_layout.addWidget(self.choice_confirm_btn)
        layout.addLayout(self.choice_confirm_layout)

        self.learn_feedback = QLabel("")
        self.learn_feedback.setAlignment(Qt.AlignCenter)
        self.learn_feedback.setFont(QFont("Arial", 15, QFont.Bold))
        self.learn_feedback.setStyleSheet("padding: 2px;")
        layout.addWidget(self.learn_feedback)

        self.next_btn_layout = QHBoxLayout()
        self.next_btn_layout.addStretch()
        self.next_btn = create_styled_button("➡️ 下一题", self.next_learn_question, "#3498db", 40, 14)
        self.next_btn.setVisible(False)
        self.next_btn_layout.addWidget(self.next_btn)
        layout.addLayout(self.next_btn_layout)

        self.learn_status = QLabel("")
        self.learn_status.setAlignment(Qt.AlignCenter)
        self.learn_status.setFont(QFont("Arial", 10))
        self.learn_status.setStyleSheet("color: #95a5a6; padding: 2px;")
        layout.addWidget(self.learn_status)

        self.learn_input.setEnabled(False)
        self.learn_submit_btn.setEnabled(False)
        self.judge_btn_1.setVisible(False)
        self.judge_btn_2.setVisible(False)
        self.judge_btn_3.setVisible(False)
        self.choice_confirm_btn.setVisible(False)

        return page

    def back_from_learn(self):
        """返回学习选择界面，弹窗询问是否保存进度"""
        if self.is_in_learn and self.learn_session and self.learn_session.has_next():
            reply = QMessageBox.question(
                self, "保存进度",
                "当前学习进度尚未完成，是否保存进度？\n\n选择「是」保存进度\n选择「否」不保存直接退出",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
            )
            if reply == QMessageBox.Yes:
                self.safe_save_progress()
            elif reply == QMessageBox.No:
                if self.current_level and self.current_temps:
                    clear_progress(self.current_level, self.current_temps)
            else:
                return
        
        self.is_in_learn = False
        self.show_nav()
        self.switch_page("home")

    def show_current_round(self):
        try:
            session = self.learn_session
            if session is None:
                QMessageBox.warning(self, "错误", "学习会话丢失，请重新开始")
                self.back_to_learn_select()
                return

            if len(session.queue) == 0:
                self.learn_group_index += 1
                if self.learn_group_index < len(self.learn_groups):
                    random.shuffle(self.learn_groups[self.learn_group_index])
                    session.queue = self.learn_groups[self.learn_group_index]
                    session.index = 0
                else:
                    self.is_in_learn = False
                    if self.current_level and self.current_temps:
                        clear_progress(self.current_level, self.current_temps)
                    QMessageBox.information(self, "🎉", "所有组学习完成！")
                    self.show_nav()
                    self.back_to_learn_select()
                    return

            if session.index >= len(session.queue):
                session.index = 0

            session.get_current_entry()
            if session.current_entry is None:
                session.queue.pop(0)
                QTimer.singleShot(100, self.show_current_round)
                return

            round_name = session.current_entry.get('round', 'judge')
            done, total = session.get_progress()
            self.learn_progress_label.setText(f"进度：{done} / {total}")
            self.learn_round_label.setText(f"当前：{session.get_current_round_name()}")

            self.clear_layout(self.learn_judge_grid)

            if round_name == "judge":
                self.show_judge_round()
            elif round_name == "reverse":
                self.show_reverse_round()
            elif round_name == "choice":
                self.show_choice_round()
            elif round_name == "fill":
                self.show_fill_round()
            else:
                self.show_judge_round()

            self.safe_save_progress()
        except Exception as e:
            print(f"显示当前轮次失败：{e}")

    def show_judge_round(self):
        try:
            session = self.learn_session
            entry = session.current_entry
            all_conjugaisons = session.get_judge_display()

            self.learn_question_label.setText(f"词条：{entry['verbe']} - {entry['temps']}")
            self.learn_hint_label.setText("请查看以下所有变位，选择掌握程度：")

            personnes = ["je", "tu", "il", "nous", "vous", "ils"]
            for i, pers in enumerate(personnes):
                display_pers = "il/elle" if pers == "il" else "ils/elles" if pers == "ils" else pers
                conjugaison = all_conjugaisons.get(pers, "—")
                label = QLabel(f"{display_pers}: {conjugaison}")
                label.setFont(QFont("Arial", 14))
                if conjugaison == "—":
                    label.setStyleSheet("background: #ecf0f1; padding: 6px; border-radius: 6px; color: #bdc3c7;")
                else:
                    label.setStyleSheet("background: #ecf0f1; padding: 6px; border-radius: 6px;")
                self.learn_judge_grid.addWidget(label, i // 2, i % 2)

            self.judge_btn_1.setVisible(True)
            self.judge_btn_2.setVisible(True)
            self.judge_btn_3.setVisible(True)
            self.learn_input.setVisible(False)
            self.learn_submit_btn.setVisible(False)
            self.choice_confirm_btn.setVisible(False)
            self.next_btn.setVisible(False)
            self.learn_feedback.setText("")
            self.clear_layout(self.choice_layout)
        except Exception as e:
            print(f"显示判断轮失败：{e}")

    def process_judge(self, choice):
        try:
            session = self.learn_session
            if session is None or session.current_entry is None:
                return

            entry = session.current_entry
            
            if choice == 1:
                for personne in entry['personnes']:
                    ajouter_maitrise(entry['verbe'], entry['temps'], personne)
                session.queue.pop(session.index)
                if session.index >= len(session.queue):
                    session.index = 0
                self.learn_feedback.setText("✅ 已标记为掌握！")
                self.learn_feedback.setStyleSheet("color: #2ecc71; font-weight: bold; padding: 2px;")
            elif choice == 2:
                entry['round'] = "choice"
                entry['choice_skip'] = True
                session.index += 1
                if session.index >= len(session.queue):
                    session.index = 0
                self.learn_feedback.setText("⏭️ 进入选择题")
                self.learn_feedback.setStyleSheet("color: #f39c12; font-weight: bold; padding: 2px;")
            else:
                entry['round'] = "reverse"
                session.index += 1
                if session.index >= len(session.queue):
                    session.index = 0
                self.learn_feedback.setText("⏭️ 进入反向选择")
                self.learn_feedback.setStyleSheet("color: #f39c12; font-weight: bold; padding: 2px;")

            self.judge_btn_1.setVisible(False)
            self.judge_btn_2.setVisible(False)
            self.judge_btn_3.setVisible(False)

            if len(session.queue) == 0:
                self.learn_group_index += 1
                if self.learn_group_index < len(self.learn_groups):
                    random.shuffle(self.learn_groups[self.learn_group_index])
                    session.queue = self.learn_groups[self.learn_group_index]
                    session.index = 0
                    self.safe_save_progress()
                    QTimer.singleShot(500, self.show_current_round)
                    return
                else:
                    self.is_in_learn = False
                    clear_progress(self.current_level, self.current_temps)
                    QMessageBox.information(self, "🎉", "所有组学习完成！")
                    self.show_nav()
                    self.back_to_learn_select()
                    return

            self.safe_save_progress()
            QTimer.singleShot(500, self.show_current_round)
        except Exception as e:
            print(f"处理判断轮失败：{e}")
            if self.learn_session and len(self.learn_session.queue) > 0:
                self.learn_session.queue.pop(0)
            self.safe_save_progress()
            QTimer.singleShot(500, self.show_current_round)

    def show_reverse_round(self):
        try:
            session = self.learn_session
            if not session.settings.get('enable_reverse', True):
                session.current_entry['round'] = "choice"
                self.show_current_round()
                return

            personne = session.get_current_personne()
            if personne is None:
                self.show_current_round()
                return
            qdata = session.get_question_data_for_personne(personne)
            if qdata is None:
                self.show_current_round()
                return

            v = session.current_entry['verbe']
            t = session.current_entry['temps']
            all_conjugaisons = get_judge_display_data(session.data_dict, v, t)

            personnes = ["je", "tu", "il", "nous", "vous", "ils"]
            options = []
            for p in personnes:
                if p in all_conjugaisons:
                    display_p = "il/elle" if p == "il" else "ils/elles" if p == "ils" else p
                    options.append({
                        "personne": p,
                        "display": display_p
                    })

            self._reverse_data = {
                "conjugaison": qdata['conjugaison'],
                "temps": t,
                "verbe": v,
                "correct_personne": personne,
                "options": options
            }
            self._selected_reverse = None

            self.learn_title.setText("📚 学习 - 反向选择")
            self.learn_question_label.setText(
                f"变位：{qdata['conjugaison']}\n"
                f"动词：{v}  |  时态：{t}"
            )
            self.learn_hint_label.setText("请选择这个变位对应的人称：")

            self.clear_layout(self.choice_layout)
            self.choice_buttons = []

            for opt in self._reverse_data['options']:
                btn = QPushButton(opt['display'])
                btn.setFont(QFont("Arial", 14))
                btn.setMinimumHeight(40)
                btn.setStyleSheet("""
                    QPushButton {
                        background: white;
                        border: 2px solid #dcdde1;
                        border-radius: 8px;
                        padding: 6px 12px;
                        text-align: center;
                    }
                    QPushButton:hover {
                        border: 2px solid #3498db;
                        background: #e8f0fe;
                    }
                    QPushButton:checked {
                        border: 2px solid #3498db;
                        background: #d6eaf8;
                    }
                """)
                btn.setCursor(Qt.PointingHandCursor)
                btn.setCheckable(True)
                btn.personne = opt['personne']
                btn.clicked.connect(lambda checked, b=btn: self.select_reverse_option(b))
                self.choice_layout.addWidget(btn)
                self.choice_buttons.append(btn)

            self.choice_confirm_btn.setVisible(True)
            self.choice_confirm_btn.setEnabled(False)
            self.choice_confirm_btn.clicked.disconnect()
            self.choice_confirm_btn.clicked.connect(self.confirm_reverse_choice)

            self.learn_input.setVisible(False)
            self.learn_submit_btn.setVisible(False)
            self.judge_btn_1.setVisible(False)
            self.judge_btn_2.setVisible(False)
            self.judge_btn_3.setVisible(False)
            self.next_btn.setVisible(False)
            self.learn_feedback.setText("")
        except Exception as e:
            print(f"显示反向轮失败：{e}")

    def select_reverse_option(self, btn):
        for b in self.choice_buttons:
            if b != btn:
                b.setChecked(False)
        self._selected_reverse = btn
        self.choice_confirm_btn.setEnabled(True)

    def confirm_reverse_choice(self):
        try:
            if self._selected_reverse is None:
                return

            session = self.learn_session
            correct_personne = self._reverse_data['correct_personne']
            selected_personne = self._selected_reverse.personne

            for btn in self.choice_buttons:
                btn.setEnabled(False)
            self.choice_confirm_btn.setVisible(False)
            self.choice_confirm_btn.setEnabled(False)

            if selected_personne == correct_personne:
                display_correct = "il/elle" if correct_personne == "il" else "ils/elles" if correct_personne == "ils" else correct_personne
                self.learn_feedback.setText(f"✅ 完全正确！对应人称是：{display_correct}")
                self.learn_feedback.setStyleSheet("color: #2ecc71; font-weight: bold; padding: 2px;")
                incrementer_correct(self.stats)
                session.process_reverse(True)
                self.safe_save_progress()
                QTimer.singleShot(800, self.show_current_round)
            else:
                qdata = session.get_question_data_for_personne(correct_personne)
                display_correct = "il/elle" if correct_personne == "il" else "ils/elles" if correct_personne == "ils" else correct_personne
                display_selected = "il/elle" if selected_personne == "il" else "ils/elles" if selected_personne == "ils" else selected_personne
                self.learn_feedback.setText(f"❌ 错误！正确答案是：{display_correct}，你选了：{display_selected}")
                self.learn_feedback.setStyleSheet("color: #e74c3c; font-weight: bold; padding: 2px;")
                if qdata:
                    sauvegarder_erreur(qdata['verbe'], qdata['temps'], qdata['personne'], qdata['conjugaison'])
                incrementer_total(self.stats)
                session.process_reverse(False)
                self.safe_save_progress()
                self.next_btn.setText("➡️ 下一题")
                self.next_btn.setVisible(True)
        except Exception as e:
            print(f"确认反向选择失败：{e}")

    def show_choice_round(self):
        try:
            session = self.learn_session
            if not session.settings.get('enable_choice', True):
                session.current_entry['round'] = "fill"
                self.show_current_round()
                return

            if session.should_skip_choice():
                session.current_entry['round'] = "fill"
                self.show_current_round()
                return

            qdata = session.get_question_data_for_personne(session.get_current_personne())
            if qdata is None:
                self.show_current_round()
                return

            options = session.get_options()

            display_pers = "il/elle" if qdata['personne'] == "il" else "ils/elles" if qdata['personne'] == "ils" else qdata['personne']
            self.learn_question_label.setText(
                f"动词：{qdata['verbe']}  |  时态：{qdata['temps']}  |  人称：{display_pers}"
            )
            self.learn_hint_label.setText("请选择正确的变位：")

            self.clear_layout(self.choice_layout)
            self.choice_buttons = []

            session.selected_choice = None
            session.is_waiting_confirm = False

            for i, opt in enumerate(options):
                btn = QPushButton(f"{i+1}. {opt}")
                btn.setFont(QFont("Arial", 13))
                btn.setMinimumHeight(38)
                btn.setStyleSheet("""
                    QPushButton {
                        background: white;
                        border: 2px solid #dcdde1;
                        border-radius: 8px;
                        padding: 6px 12px;
                        text-align: left;
                    }
                    QPushButton:hover {
                        border: 2px solid #3498db;
                        background: #e8f0fe;
                    }
                    QPushButton:checked {
                        border: 2px solid #3498db;
                        background: #d6eaf8;
                    }
                """)
                btn.setCursor(Qt.PointingHandCursor)
                btn.setCheckable(True)
                btn.clicked.connect(lambda checked, b=btn, o=opt: self.select_choice_option(b, o))
                self.choice_layout.addWidget(btn)
                self.choice_buttons.append(btn)

            self.learn_input.setVisible(False)
            self.learn_submit_btn.setVisible(False)
            self.choice_confirm_btn.setVisible(True)
            self.choice_confirm_btn.setEnabled(False)
            self.choice_confirm_btn.clicked.disconnect()
            self.choice_confirm_btn.clicked.connect(self.confirm_choice)
            self.judge_btn_1.setVisible(False)
            self.judge_btn_2.setVisible(False)
            self.judge_btn_3.setVisible(False)
            self.next_btn.setVisible(False)
            self.learn_feedback.setText("")
        except Exception as e:
            print(f"显示选择轮失败：{e}")

    def select_choice_option(self, btn, option):
        for b in self.choice_buttons:
            if b != btn:
                b.setChecked(False)
        self.learn_session.selected_choice = option
        self.learn_session.is_waiting_confirm = True
        self.choice_confirm_btn.setEnabled(True)

    def confirm_choice(self):
        try:
            session = self.learn_session
            if not session.is_waiting_confirm or session.selected_choice is None:
                return

            personne = session.get_current_personne()
            qdata = session.get_question_data_for_personne(personne)
            if qdata is None:
                return

            correct = qdata['conjugaison']
            fuzzy = session.settings.get('fuzzy', True)
            ok = verifier_reponse(session.selected_choice, correct, fuzzy)

            session.is_waiting_confirm = False
            self.choice_confirm_btn.setVisible(False)
            self.choice_confirm_btn.setEnabled(False)

            for btn in self.choice_buttons:
                btn.setEnabled(False)

            if ok:
                self.learn_feedback.setText("✅ 完全正确！🎉")
                self.learn_feedback.setStyleSheet("color: #2ecc71; font-weight: bold; padding: 2px;")
                incrementer_correct(self.stats)
                session.process_choice(True)
                self.safe_save_progress()
                QTimer.singleShot(600, self.show_current_round)
            else:
                self.learn_feedback.setText(f"❌ 错误！正确答案：{correct}")
                self.learn_feedback.setStyleSheet("color: #e74c3c; font-weight: bold; padding: 2px;")
                sauvegarder_erreur(qdata['verbe'], qdata['temps'], qdata['personne'], correct)
                incrementer_total(self.stats)
                session.process_choice(False)
                self.safe_save_progress()
                self.next_btn.setText("➡️ 下一题")
                self.next_btn.setVisible(True)
        except Exception as e:
            print(f"确认选择失败：{e}")

    def show_fill_round(self):
        try:
            session = self.learn_session
            if not session.settings.get('enable_fill', True):
                for personne in session.current_entry['personnes']:
                    ajouter_maitrise(session.current_entry['verbe'], session.current_entry['temps'], personne)
                session.queue.pop(session.index)
                if session.index >= len(session.queue):
                    session.index = len(session.queue) - 1
                self.show_current_round()
                return

            if session.should_skip_fill():
                for personne in session.current_entry['personnes']:
                    ajouter_maitrise(session.current_entry['verbe'], session.current_entry['temps'], personne)
                session.queue.pop(session.index)
                if session.index >= len(session.queue):
                    session.index = len(session.queue) - 1
                self.show_current_round()
                return

            personne = session.get_current_personne()
            qdata = session.get_question_data_for_personne(personne)
            if qdata is None:
                self.show_current_round()
                return

            display_pers = "il/elle" if qdata['personne'] == "il" else "ils/elles" if qdata['personne'] == "ils" else qdata['personne']
            self.learn_question_label.setText(
                f"动词：{qdata['verbe']}  |  时态：{qdata['temps']}  |  人称：{display_pers}"
            )
            self.learn_hint_label.setText("请输入正确的变位")

            self.learn_input.setVisible(True)
            self.learn_submit_btn.setVisible(True)
            self.learn_input.setEnabled(True)
            self.learn_submit_btn.setEnabled(True)
            self.learn_input.clear()
            self.learn_input.setFocus()

            self.judge_btn_1.setVisible(False)
            self.judge_btn_2.setVisible(False)
            self.judge_btn_3.setVisible(False)
            self.choice_confirm_btn.setVisible(False)
            self.next_btn.setVisible(False)
            self.learn_feedback.setText("")
            self.clear_layout(self.choice_layout)
        except Exception as e:
            print(f"显示填空轮失败：{e}")

    def submit_learn_answer(self):
        try:
            session = self.learn_session
            round_name = session.current_entry.get('round', 'judge')

            if round_name != "fill":
                return

            user_input = self.learn_input.text().strip()
            if not user_input:
                self.learn_feedback.setText("⚠️ 请输入答案！")
                self.learn_feedback.setStyleSheet("color: orange; font-weight: bold; padding: 2px;")
                return

            personne = session.get_current_personne()
            qdata = session.get_question_data_for_personne(personne)
            if qdata is None:
                return

            expected = qdata['conjugaison']
            ok = session.check_answer(user_input, expected)

            if ok:
                self.learn_feedback.setText("✅ 完全正确！🎉")
                self.learn_feedback.setStyleSheet("color: #2ecc71; font-weight: bold; padding: 2px;")
                incrementer_correct(self.stats)
                session.process_fill(True)
                self.safe_save_progress()
                self.learn_input.setEnabled(False)
                self.learn_submit_btn.setEnabled(False)
                QTimer.singleShot(600, self.show_current_round)
            else:
                self.learn_feedback.setText(f"❌ 错误！正确答案：{expected}")
                self.learn_feedback.setStyleSheet("color: #e74c3c; font-weight: bold; padding: 2px;")
                sauvegarder_erreur(qdata['verbe'], qdata['temps'], qdata['personne'], expected)
                incrementer_total(self.stats)
                self.learn_input.setEnabled(False)
                self.learn_submit_btn.setEnabled(False)
                session.process_fill(False)
                self.safe_save_progress()
                self.next_btn.setText("➡️ 继续")
                self.next_btn.setVisible(True)
        except Exception as e:
            print(f"提交学习答案失败：{e}")

    def next_learn_question(self):
        self.next_btn.setVisible(False)
        self.learn_input.setEnabled(True)
        self.learn_submit_btn.setEnabled(True)
        self.learn_input.setFocus()
        self.show_current_round()

    def clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    # ================================================================
    #                         复习页
    # ================================================================

    def create_review_page(self):
        page = QWidget()
        page.setStyleSheet("background: #f5f6fa;")
        layout = QVBoxLayout()
        page.setLayout(layout)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)

        top_layout = QHBoxLayout()
        back_btn = QPushButton("⬅️ 返回")
        back_btn.setFont(QFont("Arial", 12, QFont.Bold))
        back_btn.setMinimumHeight(35)
        back_btn.setFixedWidth(100)
        back_btn.setStyleSheet("""
            QPushButton {
                background: #e74c3c;
                color: white;
                border-radius: 8px;
                border: none;
                padding: 4px 12px;
            }
            QPushButton:hover { background: #c0392b; }
        """)
        back_btn.clicked.connect(self.back_from_review)
        top_layout.addWidget(back_btn)

        top_layout.addStretch()
        self.review_title = QLabel("🔄 复习")
        self.review_title.setFont(QFont("Arial", 16, QFont.Bold))
        self.review_title.setStyleSheet("color: #2c3e50;")
        top_layout.addWidget(self.review_title)
        top_layout.addStretch()
        layout.addLayout(top_layout)

        self.review_progress_label = QLabel("复习进度：0 / 0")
        self.review_progress_label.setAlignment(Qt.AlignCenter)
        self.review_progress_label.setFont(QFont("Arial", 12))
        self.review_progress_label.setStyleSheet("color: #7f8c8d; padding: 2px;")
        layout.addWidget(self.review_progress_label)

        self.review_question_label = QLabel("准备开始复习")
        self.review_question_label.setAlignment(Qt.AlignCenter)
        self.review_question_label.setFont(QFont("Arial", 18, QFont.Bold))
        self.review_question_label.setMinimumHeight(60)
        self.review_question_label.setStyleSheet("""
            background: white;
            padding: 16px;
            border-radius: 14px;
            border: none;
            color: #2c3e50;
        """)
        layout.addWidget(self.review_question_label)

        self.review_hint_label = QLabel("")
        self.review_hint_label.setAlignment(Qt.AlignCenter)
        self.review_hint_label.setFont(QFont("Arial", 13))
        self.review_hint_label.setStyleSheet("color: #2ecc71; padding: 2px; font-weight: bold;")
        layout.addWidget(self.review_hint_label)

        input_layout = QHBoxLayout()
        input_layout.setSpacing(10)
        self.review_input = QLineEdit()
        self.review_input.setPlaceholderText("✏️ 输入变位...")
        self.review_input.setFont(QFont("Arial", 16))
        self.review_input.setMinimumHeight(42)
        self.review_input.setStyleSheet("""
            QLineEdit {
                border: 2px solid #dcdde1;
                border-radius: 10px;
                padding: 4px 12px;
                background: white;
            }
            QLineEdit:focus {
                border: 2px solid #3498db;
            }
        """)
        self.review_input.returnPressed.connect(self.submit_review_answer)
        input_layout.addWidget(self.review_input)

        self.review_submit_btn = QPushButton("✅ 提交")
        self.review_submit_btn.setFont(QFont("Arial", 13, QFont.Bold))
        self.review_submit_btn.setMinimumHeight(42)
        self.review_submit_btn.setFixedWidth(90)
        self.review_submit_btn.setCursor(Qt.PointingHandCursor)
        self.review_submit_btn.setStyleSheet("""
            QPushButton {
                background: #e67e22;
                color: white;
                border-radius: 10px;
                border: none;
                padding: 4px 10px;
            }
            QPushButton:hover { background: #d35400; }
        """)
        self.review_submit_btn.clicked.connect(self.submit_review_answer)
        input_layout.addWidget(self.review_submit_btn)
        layout.addLayout(input_layout)

        self.review_feedback = QLabel("")
        self.review_feedback.setAlignment(Qt.AlignCenter)
        self.review_feedback.setFont(QFont("Arial", 15, QFont.Bold))
        self.review_feedback.setStyleSheet("padding: 2px;")
        layout.addWidget(self.review_feedback)

        self.review_status = QLabel("")
        self.review_status.setAlignment(Qt.AlignCenter)
        self.review_status.setFont(QFont("Arial", 10))
        self.review_status.setStyleSheet("color: #95a5a6; padding: 2px;")
        layout.addWidget(self.review_status)

        self.review_input.setEnabled(False)
        self.review_submit_btn.setEnabled(False)

        return page

    def back_from_review(self):
        if self.is_in_review and self.review_session and self.review_session.has_next():
            review_progress = {
                "index": self.review_session.index,
                "sub_index": self.review_session.sub_index,
                "keys": self.review_session.keys
            }
            set_review_progress(review_progress)
        self.is_in_review = False
        self.show_nav()
        self.switch_page("home")

    def prepare_review(self):
        try:
            self.hide_nav()
            
            # 从文件加载完整数据
            all_data = load_all_data()
            data_dict = {}
            for verbe, levels in all_data.items():
                for level, temps_dict in levels.items():
                    for temps, pers_dict in temps_dict.items():
                        for personne, conjugaison in pers_dict.items():
                            data_dict[(verbe, temps, personne)] = (conjugaison, "", "")
            
            self.review_session = ReviewSession(data_dict, self.settings)
            
            saved_progress = get_review_progress()
            if saved_progress and saved_progress.get('keys'):
                if saved_progress['keys'] == self.review_session.keys:
                    self.review_session.index = saved_progress.get('index', 0)
                    self.review_session.sub_index = saved_progress.get('sub_index', 0)
                    self.review_session.is_completed = False
            
            if self.review_session.is_empty():
                self.review_question_label.setText("🎉 没有需要复习的单词！")
                self.review_input.setEnabled(False)
                self.review_submit_btn.setEnabled(False)
                self.review_progress_label.setText("复习进度：0 / 0")
                self.show_nav()
                return
            
            self.is_in_review = True
            self.show_review_question()
        except Exception as e:
            print(f"准备复习失败：{e}")
            self.show_nav()

    def show_review_question(self):
        try:
            session = self.review_session

            if not session.has_next():
                self.review_question_label.setText("🎉 所有复习已完成！")
                self.review_input.setEnabled(False)
                self.review_submit_btn.setEnabled(False)
                clear_review_progress()
                self.is_in_review = False
                self.show_nav()
                return

            item = session.load_next_question()
            if item is None:
                self.review_question_label.setText("🎉 所有复习已完成！")
                self.review_input.setEnabled(False)
                self.review_submit_btn.setEnabled(False)
                clear_review_progress()
                self.is_in_review = False
                self.show_nav()
                return

            qdata = session.get_current_question_data()
            if qdata is None or not qdata.get('exists', False):
                # 数据不存在，跳过
                session.advance()
                QTimer.singleShot(100, self.show_review_question)
                return

            # 显示原型和时态，不显示人称
            self.review_question_label.setText(
                f"🔄 复习：{qdata['verbe']} - {qdata['temps']}"
            )
            self.review_hint_label.setText(f"请输入 {qdata['verbe']} 的变位")

            self.review_input.clear()
            self.review_input.setEnabled(True)
            self.review_submit_btn.setEnabled(True)
            self.review_input.setFocus()
            self.review_feedback.setText("")

            done, total = session.get_progress()
            self.review_progress_label.setText(f"复习进度：{done} / {total}")
        except Exception as e:
            print(f"显示复习题失败：{e}")

    def submit_review_answer(self):
        try:
            session = self.review_session
            user_input = self.review_input.text().strip()

            if not user_input:
                self.review_feedback.setText("⚠️ 请输入答案！")
                self.review_feedback.setStyleSheet("color: orange; font-weight: bold; padding: 2px;")
                return

            ok, correct = session.check_answer(user_input)

            if ok:
                self.review_feedback.setText("✅ 正确！")
                self.review_feedback.setStyleSheet("color: #2ecc71; font-weight: bold; padding: 2px;")
                self.review_input.setEnabled(False)
                self.review_submit_btn.setEnabled(False)
                review_progress = {
                    "index": session.index,
                    "sub_index": session.sub_index,
                    "keys": session.keys
                }
                set_review_progress(review_progress)
                QTimer.singleShot(500, self.show_review_question)
            else:
                self.review_feedback.setText(f"❌ 错误！正确答案：{correct}")
                self.review_feedback.setStyleSheet("color: #e74c3c; font-weight: bold; padding: 2px;")
                self.review_input.setFocus()
                self.review_input.selectAll()
        except Exception as e:
            print(f"提交复习答案失败：{e}")

    # ================================================================
    #                         错题本
    # ================================================================

    def create_errors_page(self):
        page = QWidget()
        page.setStyleSheet("background: #f5f6fa;")
        layout = QVBoxLayout()
        page.setLayout(layout)
        layout.setSpacing(12)
        layout.setContentsMargins(5, 5, 5, 5)

        title = QLabel("📕 错题本")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont("Arial", 20, QFont.Bold))
        title.setStyleSheet("color: #2c3e50;")
        layout.addWidget(title)

        self.errors_list = QListWidget()
        self.errors_list.setFont(QFont("Arial", 12))
        self.errors_list.setStyleSheet("""
            QListWidget {
                background: white;
                border: none;
                border-radius: 12px;
                padding: 8px;
            }
            QListWidget::item {
                padding: 6px 10px;
                border-bottom: 1px solid #ecf0f1;
            }
            QListWidget::item:selected {
                background: #e8f0fe;
                color: #2c3e50;
            }
        """)
        layout.addWidget(self.errors_list)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(6)
        for text, callback, color in [
            ("🗑️ 删除", self.delete_selected_error, "#e67e22"),
            ("🗑️ 清空", self.safe_clear_all_errors, "#e74c3c"),
            ("🔄 刷新", self.refresh_errors_list, "#3498db")
        ]:
            btn = create_styled_button(text, callback, color, 36, 12)
            btn_layout.addWidget(btn)
        layout.addLayout(btn_layout)

        self.errors_status = QLabel("")
        self.errors_status.setAlignment(Qt.AlignCenter)
        self.errors_status.setFont(QFont("Arial", 11))
        self.errors_status.setStyleSheet("color: #95a5a6; padding: 2px;")
        layout.addWidget(self.errors_status)

        return page

    def refresh_errors_list(self):
        try:
            if hasattr(self, 'errors_list'):
                self.errors_list.clear()
                erreurs = charger_erreurs()
                self.errors_items = list(erreurs.items())

                if not erreurs:
                    add_empty_item(self.errors_list, "🎉 错题本为空，继续加油！")
                    self.errors_status.setText("📕 暂无错题")
                    return

                for (v, t, p), c in self.errors_items:
                    display_p = "il/elle" if p == "il" else "ils/elles" if p == "ils" else p
                    self.errors_list.addItem(f"{v} - {t} - {display_p}  →  {c}")
                self.errors_status.setText(f"📕 共 {len(self.errors_items)} 道错题")
        except Exception as e:
            print(f"刷新错题本失败：{e}")

    def delete_selected_error(self):
        try:
            current = self.errors_list.currentRow()
            if current < 0 or current >= len(self.errors_items):
                QMessageBox.warning(self, "提示", "请先选中要删除的错题！")
                return
            erreurs = charger_erreurs()
            del erreurs[self.errors_items[current][0]]
            ecrire_tout_erreurs(erreurs)
            self.refresh_errors_list()
            self.update_main_status()
            QMessageBox.information(self, "成功", "已删除该错题！")
        except Exception as e:
            print(f"删除错题失败：{e}")

    def safe_clear_all_errors(self):
        try:
            reply = QMessageBox.question(self, "确认", "确定要清空所有错题吗？", QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                fichier = FILES['erreurs']
                if os.path.exists(fichier):
                    backup_file(fichier)
                    with open(fichier, 'w', encoding='utf-8') as f:
                        f.write("verbe,temps,personne,conjugaison\n")
                    self.refresh_errors_list()
                    self.update_main_status()
                    QMessageBox.information(self, "成功", "已清空所有错题！")
        except Exception as e:
            print(f"清空错题失败：{e}")
            QMessageBox.warning(self, "错误", f"清空失败：{str(e)}")

    # ================================================================
    #                         掌握库
    # ================================================================

    def create_mastered_page(self):
        page = QWidget()
        page.setStyleSheet("background: #f5f6fa;")
        layout = QVBoxLayout()
        page.setLayout(layout)
        layout.setSpacing(12)
        layout.setContentsMargins(5, 5, 5, 5)

        title = QLabel("📖 掌握库")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont("Arial", 20, QFont.Bold))
        title.setStyleSheet("color: #2c3e50;")
        layout.addWidget(title)

        self.mastered_list = QListWidget()
        self.mastered_list.setFont(QFont("Arial", 12))
        self.mastered_list.setStyleSheet("""
            QListWidget {
                background: white;
                border: none;
                border-radius: 12px;
                padding: 8px;
            }
            QListWidget::item {
                padding: 6px 10px;
                border-bottom: 1px solid #ecf0f1;
            }
            QListWidget::item:selected {
                background: #e8f0fe;
                color: #2c3e50;
            }
        """)
        layout.addWidget(self.mastered_list)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        reword_btn = create_styled_button("📤 放入生词", self.reword_selected, "#e67e22", 40, 14)
        btn_layout.addWidget(reword_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self.mastered_status = QLabel("")
        self.mastered_status.setAlignment(Qt.AlignCenter)
        self.mastered_status.setFont(QFont("Arial", 11))
        self.mastered_status.setStyleSheet("color: #95a5a6; padding: 2px;")
        layout.addWidget(self.mastered_status)

        return page

    def refresh_mastered_list(self):
        try:
            if hasattr(self, 'mastered_list'):
                self.mastered_list.clear()
                maitrises = charger_maitrises()
                
                # 按 (verbe, temps) 分组，合并所有人称
                classes = {}
                for item in maitrises:
                    key = (item['verbe'], item['temps'])
                    if key not in classes:
                        classes[key] = {
                            'verbe': item['verbe'],
                            'temps': item['temps'],
                            'personnes': [],
                            'days': item.get('days', 1),
                            'needs_review': item.get('needs_review', False)
                        }
                    classes[key]['personnes'].append(item['personne'])
                
                self.mastered_items = list(classes.values())
                self.mastered_items.sort(key=lambda x: x['verbe'])
                
                if not self.mastered_items:
                    add_empty_item(self.mastered_list, "📖 暂无已掌握的单词，快去学习吧！")
                    self.mastered_status.setText("📖 暂无已掌握词条")
                    return
                
                for idx, item in enumerate(self.mastered_items):
                    v = item['verbe']
                    t = item['temps']
                    days = item.get('days', 1)
                    needs = item.get('needs_review', False)
                    personnes = item['personnes']
                    
                    display_pers = []
                    for p in personnes:
                        if p == "il":
                            display_pers.append("il/elle")
                        elif p == "ils":
                            display_pers.append("ils/elles")
                        else:
                            display_pers.append(p)
                    
                    text = f"{v} - {t}  ({', '.join(display_pers)})  学习{days}天"
                    if needs:
                        text += " ⚠️需复习"
                    
                    widget = QWidget()
                    layout = QHBoxLayout()
                    layout.setContentsMargins(5, 2, 5, 2)
                    layout.setSpacing(10)
                    
                    checkbox = QCheckBox()
                    checkbox.setStyleSheet("QCheckBox { margin-right: 8px; }")
                    checkbox.stateChanged.connect(lambda state, i=idx: self.on_mastered_checkbox_changed(i, state))
                    layout.addWidget(checkbox)
                    
                    label = QLabel(text)
                    label.setFont(QFont("Arial", 12))
                    label.setWordWrap(True)
                    label.setMinimumWidth(300)
                    layout.addWidget(label)
                    
                    layout.addStretch()
                    widget.setLayout(layout)
                    
                    item_widget = QListWidgetItem()
                    item_widget.setSizeHint(widget.sizeHint())
                    self.mastered_list.addItem(item_widget)
                    self.mastered_list.setItemWidget(item_widget, widget)
                
                self.mastered_status.setText(f"📖 共 {len(self.mastered_items)} 类已掌握词条")
        except Exception as e:
            print(f"刷新掌握库失败：{e}")

    def on_mastered_checkbox_changed(self, index, state):
        pass

    def reword_selected(self):
        try:
            selected_indices = []
            for i in range(self.mastered_list.count()):
                item = self.mastered_list.item(i)
                widget = self.mastered_list.itemWidget(item)
                if widget:
                    checkbox = widget.findChild(QCheckBox)
                    if checkbox and checkbox.isChecked():
                        selected_indices.append(i)
            
            if not selected_indices:
                QMessageBox.warning(self, "提示", "请先勾选要操作的词条！")
                return
            
            reply = QMessageBox.question(
                self, "确认放入生词",
                f"确定要将选中的 {len(selected_indices)} 个词条放回生词库吗？",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return
            
            for idx in selected_indices:
                if idx < len(self.mastered_items):
                    item = self.mastered_items[idx]
                    for p in item['personnes']:
                        remove_from_maitrise(item['verbe'], item['temps'], p)
            
            self.refresh_mastered_list()
            self.update_main_status()
            QMessageBox.information(self, "成功", f"已成功放入生词 {len(selected_indices)} 个词条！")
        except Exception as e:
            print(f"放入生词失败：{e}")
            QMessageBox.warning(self, "错误", f"操作失败：{str(e)}")

    # ================================================================
    #                         查找功能
    # ================================================================

    def create_search_page(self):
        page = QWidget()
        page.setStyleSheet("background: #f5f6fa;")
        layout = QVBoxLayout()
        page.setLayout(layout)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("🔍 查找动词变位")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont("Arial", 20, QFont.Bold))
        title.setStyleSheet("color: #2c3e50;")
        layout.addWidget(title)

        search_layout = QHBoxLayout()
        search_layout.setSpacing(10)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入动词原形...")
        self.search_input.setFont(QFont("Arial", 16))
        self.search_input.setMinimumHeight(45)
        self.search_input.setStyleSheet("""
            QLineEdit {
                border: 2px solid #dcdde1;
                border-radius: 10px;
                padding: 4px 12px;
                background: white;
            }
            QLineEdit:focus {
                border: 2px solid #3498db;
            }
        """)
        self.search_input.returnPressed.connect(self.do_search)
        self.search_input.textChanged.connect(self.on_search_text_changed)
        search_layout.addWidget(self.search_input)

        search_btn = create_styled_button("🔍 查找", self.do_search, "#3498db", 45, 14)
        search_layout.addWidget(search_btn)
        layout.addLayout(search_layout)

        self.search_suggestions = QListWidget()
        self.search_suggestions.setFont(QFont("Arial", 13))
        self.search_suggestions.setMaximumHeight(120)
        self.search_suggestions.setStyleSheet("""
            QListWidget {
                background: white;
                border: 1px solid #dcdde1;
                border-radius: 8px;
                padding: 4px;
            }
            QListWidget::item:hover {
                background: #e8f0fe;
            }
            QListWidget::item:selected {
                background: #3498db;
                color: white;
            }
        """)
        self.search_suggestions.itemClicked.connect(self.on_suggestion_clicked)
        self.search_suggestions.hide()
        layout.addWidget(self.search_suggestions)

        layout.addStretch()
        return page

    def on_search_text_changed(self, text):
        if len(text) < 1:
            self.search_suggestions.hide()
            return

        all_verbs = get_all_verbs()
        text_norm = normalize(text)
        matches = []
        for v in all_verbs:
            v_norm = normalize(v)
            if text_norm in v_norm or v_norm.startswith(text_norm):
                matches.append(v)

        if matches:
            self.search_suggestions.clear()
            for v in matches[:10]:
                self.search_suggestions.addItem(v)
            self.search_suggestions.show()
            self.search_suggestions.setMaximumHeight(120)
        else:
            self.search_suggestions.hide()

    def on_suggestion_clicked(self, item):
        self.search_input.setText(item.text())
        self.search_suggestions.hide()
        self.do_search()

    def do_search(self):
        try:
            verbe = self.search_input.text().strip().lower()
            if not verbe:
                QMessageBox.warning(self, "提示", "请输入动词")
                return

            all_verbs = get_all_verbs()
            matched_verbs = []
            verbe_norm = normalize(verbe)
            for v in all_verbs:
                v_norm = normalize(v)
                if (verbe_norm in v_norm or 
                    v_norm.startswith(verbe_norm) or 
                    v_norm.endswith(verbe_norm)):
                    matched_verbs.append(v)
            
            if not matched_verbs:
                QMessageBox.information(self, "提示", f"❌ 未找到动词「{verbe}」")
                return

            verbe_found = matched_verbs[0]
            result = search_verb(verbe_found)
            if result is None:
                QMessageBox.information(self, "提示", f"❌ 未找到动词「{verbe}」")
                return

            window = SearchResultWindow(verbe_found, result, self)
            window.exec_()
            
        except Exception as e:
            print(f"搜索失败：{e}")
            QMessageBox.critical(self, "错误", f"搜索失败：{str(e)}")

    # ================================================================
    #                         设置
    # ================================================================

    def create_settings_page(self):
        page = QWidget()
        page.setStyleSheet("background: #f5f6fa;")
        layout = QVBoxLayout()
        page.setLayout(layout)
        layout.setSpacing(14)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("⚙️ 设置")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont("Arial", 20, QFont.Bold))
        title.setStyleSheet("color: #2c3e50;")
        layout.addWidget(title)

        layout.addSpacing(10)

        self.fuzzy_check = QCheckBox("🔍 开启模糊匹配")
        self.fuzzy_check.setFont(QFont("Arial", 13))
        self.fuzzy_check.setStyleSheet("padding: 4px 0;")
        layout.addWidget(self.fuzzy_check)

        self.stem_check = QCheckBox("💡 开启词干提示")
        self.stem_check.setFont(QFont("Arial", 13))
        self.stem_check.setStyleSheet("padding: 4px 0;")
        layout.addWidget(self.stem_check)

        layout.addWidget(QLabel("📝 题型设置："))
        self.reverse_check = QCheckBox("🔄 反向选择")
        self.reverse_check.setFont(QFont("Arial", 13))
        self.reverse_check.setStyleSheet("padding: 4px 0;")
        layout.addWidget(self.reverse_check)

        self.choice_check = QCheckBox("📝 选择题")
        self.choice_check.setFont(QFont("Arial", 13))
        self.choice_check.setStyleSheet("padding: 4px 0;")
        layout.addWidget(self.choice_check)

        self.fill_check = QCheckBox("✏️ 填空")
        self.fill_check.setFont(QFont("Arial", 13))
        self.fill_check.setStyleSheet("padding: 4px 0;")
        layout.addWidget(self.fill_check)

        layout.addStretch()

        save_btn = create_styled_button("💾 保存设置", self.save_settings, "#2ecc71", 48, 15)
        layout.addWidget(save_btn)

        self.refresh_settings_values()
        return page

    def refresh_settings_values(self):
        if hasattr(self, 'fuzzy_check'):
            self.fuzzy_check.setChecked(self.settings.get('fuzzy', True))
            self.stem_check.setChecked(self.settings.get('show_stem', True))
            self.reverse_check.setChecked(self.settings.get('enable_reverse', True))
            self.choice_check.setChecked(self.settings.get('enable_choice', True))
            self.fill_check.setChecked(self.settings.get('enable_fill', True))

    def save_settings(self):
        self.settings['fuzzy'] = self.fuzzy_check.isChecked()
        self.settings['show_stem'] = self.stem_check.isChecked()
        self.settings['enable_reverse'] = self.reverse_check.isChecked()
        self.settings['enable_choice'] = self.choice_check.isChecked()
        self.settings['enable_fill'] = self.fill_check.isChecked()
        sauvegarder_settings(self.settings)
        QMessageBox.information(self, "成功", "设置已保存！")

    # ================================================================
    #                         通用
    # ================================================================

    def close_app(self):
        reply = QMessageBox.question(self, "确认退出", "确定要退出程序吗？", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.safe_save_progress()
            QApplication.quit()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())