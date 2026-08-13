"""
Phone Tools Tweaker v1.0 - Кроссплатформенная адаптация для Windows и Linux (Fedora)
Changelog для Linux:
- Иконка: обёрнута в try/except, на Linux используется iconphoto с PNG (если есть).
- Перезапуск при смене языка: заменён os.execl на subprocess.Popen + sys.exit(0) для корректного завершения Tcl.
- Окружение: сначала проверяются системные adb/fastboot, при их отсутствии добавляется папка tools/.
- Shell-команды: wipe_all заменён на последовательный вызов трёх erase команд; logcat_filter теперь фильтрует вывод в Python без grep.
- Добавлена проверка на "no permissions" для fastboot с выводом инструкции по настройке udev.
- Шрифты: 'Consolas' заменён на 'monospace', 'Arial' оставлен для совместимости.
- Пути: лог-файл перенесён в каталог конфигурации (APPDATA/XDG_CONFIG_HOME).
- Окончания строк: rstrip('\n') заменён на rstrip('\r\n').
- Отмена задачи: добавлен таймаут 2 секунды перед kill, если terminate не сработал.
- Добавлен пункт меню Help -> About с информацией об ОС и путях к утилитам.
- Команда "ping device" теперь пингует 8.8.8.8 вместо localhost.
- Все изменения сохраняют полную функциональность и локализацию (ru/en).
"""

import os
import sys
import shutil
import shlex
import subprocess
import threading
import queue
import re
import tkinter as tk
from tkinter import messagebox, filedialog, ttk, simpledialog
import configparser

# --------------------- ЛОКАЛИЗАЦИЯ ---------------------
LANGUAGES = {
    'ru': {
        'app_title': 'Phone Tools Tweaker',
        'lang_choice': 'Выберите язык / Choose language:',
        'lang_ru': 'Русский',
        'lang_en': 'English',
        # Вкладки
        'tab_reboot': 'Режимы / Питание',
        'tab_info': 'Инфо и Статус',
        'tab_flash': 'Прошивка / Root',
        'tab_wipe': 'Очистка / Wipe',
        'tab_backup': 'Backup / APK',
        'tab_adb_shell': 'ADB Shell',
        'tab_pm': 'Package Manager',
        'tab_screen': 'Экран / Медиа',
        'tab_network': 'Сеть',
        'tab_settings': 'Настройки',
        'tab_log': 'Логи / Отладка',
        'tab_fb_extra': 'Fastboot Extra',
        'tab_custom': 'Произвольная команда',
        # Общие
        'check_devices': 'Проверить устройства (ADB / Fastboot)',
        'log_label': 'Вывод терминала / Лог выполнения',
        'warning_tools_missing': 'ВНИМАНИЕ: Утилиты {missing} не найдены!',
        'scan_ports': '=== Сканирование портов ===',
        'error_select_img': 'Сначала выберите файл образа!',
        'error_select_apk': 'Выберите APK файл!',
        'error_enter_cmd': 'Введите команду!',
        'confirm_flash': 'Прошить {file} в раздел {part}?',
        'confirm_erase': 'Очистить раздел {part}?',
        'confirm_format': 'Форматировать раздел {part}?',
        'confirm_uninstall': 'Удалить пакет {pkg}?',
        # Вкладка Режимы
        'adb_commands': 'Команды ADB (Когда телефон включен):',
        'fb_commands': 'Команды Fastboot (В режиме загрузчика):',
        'to_fastboot': 'В Fastboot (Bootloader)',
        'to_recovery': 'В Recovery (Рекавери)',
        'to_edl': 'В EDL (Emergency)',
        'reboot_normal': 'Обычная перезагрузка',
        'power_off': 'Выключить устройство',
        'reboot_system': 'Перезагрузить в System',
        'reboot_system_fb': 'Выйти в Систему',
        'reboot_edl_fb': 'Перезагрузить в EDL',
        'to_fastbootd': 'В Fastbootd (User space)',
        'reboot_recovery_fb': 'Перезагрузить в Recovery',
        # Вкладка Инфо
        'diag_header': 'Диагностика устройства:',
        'check_bootloader': 'Проверить статус загрузчика (Fastboot)',
        'getvar_all': 'Получить все переменные (Fastboot getvar all)',
        'get_serial': 'Показать IMEI/Серийник (Fastboot)',
        'get_prop_model': 'Характеристики железа (ADB Shell getprop)',
        'check_root': 'Проверить статус Root-прав (Su check)',
        'wm_size': 'Узнать разрешение экрана (wm size)',
        'wm_density': 'Узнать плотность экрана (wm density)',
        'dumpsys_battery': 'Информация о батарее (dumpsys battery)',
        'dumpsys_meminfo': 'Статистика памяти (dumpsys meminfo)',
        'getprop_all': 'Список всех свойств (getprop)',
        # Вкладка Прошивка
        'img_file_frame': 'Выбор файла образа (.img)',
        'browse_img': 'Обзор...',
        'partition_mgmt': 'Управление разделами (Fastboot)',
        'partition_label': 'Раздел:',
        'flash_selected': 'Прошить выбранный образ',
        'boot_selected': 'Загрузиться без прошивки (fastboot boot)',
        'slots_frame': 'Для устройств со слотами (A/B)',
        'current_slot': 'Текущий активный слот:',
        'get_slot': 'Узнать слот',
        'switch_to': 'Переключить на:',
        'change_slot': 'Сменить слот',
        'fb_extra_label': 'Дополнительные Fastboot команды',
        'unlock_bootloader': 'Разблокировать загрузчик (unlock)',
        'lock_bootloader': 'Заблокировать загрузчик (lock)',
        'unlock_info': 'Запросить код разблокировки',
        # Вкладка Wipe
        'wipe_fb_header': 'Сброс и форматирование (Режим Fastboot):',
        'erase_cache': 'Очистить кэш (fastboot erase cache)',
        'erase_userdata': 'Очистить раздел userdata (fastboot erase userdata)',
        'erase_system': 'Очистить раздел system (fastboot erase system)',
        'erase_vendor': 'Очистить раздел vendor (fastboot erase vendor)',
        'erase_boot': 'Очистить раздел boot (fastboot erase boot)',
        'erase_recovery': 'Очистить раздел recovery (fastboot erase recovery)',
        'format_userdata': 'Форматировать userdata (fastboot format userdata)',
        'format_cache': 'Форматировать cache (fastboot format cache)',
        'wipe_all': 'Очистить все разделы (wipe all) - ОСТОРОЖНО!',
        'wipe_adb_header': 'Сброс через ADB (shell):',
        'factory_reset': 'Сброс к заводским (adb shell recovery --wipe_data)',
        'trim_caches': 'Очистить кэш приложений (adb shell pm trim-caches)',
        # Вкладка Backup
        'backup_header': 'Резервное копирование (ADB):',
        'create_backup': 'Создать полный бэкап',
        'restore_backup': 'Восстановить из бэкапа',
        'apk_header': 'Установка / удаление APK:',
        'apk_frame': 'Выберите APK файл',
        'install_normal': 'Установить (обычная)',
        'install_reinstall': 'Установить (с переустановкой)',
        'install_sd': 'Установить на SD ( -s )',
        'uninstall_pkg': 'Удалить пакет (введите имя)',
        'list_all_pkgs': 'Список всех установленных пакетов',
        'list_system_pkgs': 'Список системных пакетов',
        'list_third_pkgs': 'Список сторонних пакетов',
        'pkg_path': 'Путь к APK пакета (введите имя)',
        'pull_apk': 'Выгрузить APK из устройства',
        # Вкладка ADB Shell
        'shell_system_info': 'Информация о системе',
        'shell_df': 'Свободное место на диске',
        'shell_free': 'Использование памяти',
        'shell_top': 'Топ процессов',
        'shell_ps': 'Список запущенных процессов',
        'shell_service': 'Список сервисов',
        'shell_netstat': 'Статистика сети',
        'shell_ping': 'Пинг Google',
        'shell_wifi': 'Информация о Wi-Fi',
        'shell_bluetooth': 'Информация о Bluetooth',
        'shell_power': 'Управление экраном (вкл/выкл)',
        'shell_vol_up': 'Увеличить громкость',
        'shell_vol_down': 'Уменьшить громкость',
        'shell_home': 'Домой',
        'shell_back': 'Назад',
        'shell_menu': 'Меню',
        'shell_screencap': 'Сделать скриншот (shell)',
        'shell_screenrecord': 'Запись экрана (shell, 30 сек)',
        'shell_restart_systemui': 'Перезагрузить SystemUI',
        'shell_dns': 'Очистить кэш DNS',
        # Вкладка Package Manager
        'pm_header': 'Управление пакетами (pm):',
        'pm_list_all': 'Список всех пакетов',
        'pm_list_system': 'Список системных',
        'pm_list_third': 'Список сторонних',
        'pm_list_enabled': 'Список включенных',
        'pm_list_disabled': 'Список отключенных',
        'pm_list_perms': 'Список разрешений',
        'pm_clear': 'Очистить данные пакета',
        'pm_enable': 'Включить пакет',
        'pm_disable': 'Отключить пакет',
        'pm_grant': 'Выдать разрешение',
        'pm_revoke': 'Забрать разрешение',
        'pm_path': 'Путь к APK',
        'pm_info': 'Информация о пакете',
        'pm_install': 'Установить APK',
        'pm_uninstall': 'Удалить пакет',
        # Вкладка Экран/Медиа
        'screen_header': 'Экран и медиа:',
        'screenshot_save': 'Скриншот (сохранить в /sdcard/screenshot.png)',
        'screenshot_pull': 'Выгрузить скриншот на ПК',
        'record_start': 'Начать запись экрана (30 сек, /sdcard/demo.mp4)',
        'record_pull': 'Выгрузить запись экрана',
        'set_res_1080': 'Установить разрешение 1080x1920',
        'reset_res': 'Сбросить разрешение',
        'set_density_320': 'Установить плотность 320',
        'reset_density': 'Сбросить плотность',
        'rotate_landscape': 'Повернуть экран (ландшафт)',
        'rotate_portrait': 'Повернуть экран (портрет)',
        'brightness_max': 'Увеличить яркость',
        'brightness_min': 'Уменьшить яркость (30)',
        'auto_bright_on': 'Автояркость вкл',
        'auto_bright_off': 'Автояркость выкл',
        # Вкладка Сеть
        'network_header': 'ADB по сети:',
        'adb_tcpip': 'Переключить ADB на TCP/IP (порт 5555)',
        'adb_connect_ip': 'Подключиться к устройству по IP (введите IP)',
        'adb_disconnect': 'Отключиться от устройства',
        'show_ip': 'Показать IP-адрес устройства',
        'ping_device': 'Пинг устройства (проверка связи)',
        'wifi_header': 'Wi-Fi / Bluetooth:',
        'wifi_on': 'Включить Wi-Fi',
        'wifi_off': 'Отключить Wi-Fi',
        'bluetooth_on': 'Включить Bluetooth',
        'bluetooth_off': 'Отключить Bluetooth',
        # Вкладка Настройки
        'settings_header': 'Системные настройки (settings):',
        'settings_list_global': 'Показать все системные настройки',
        'settings_list_secure': 'Показать настройки безопасности',
        'settings_list_system': 'Показать системные',
        'settings_timeout_30': 'Изменить время автоматической блокировки (30 сек)',
        'settings_timeout_5min': 'Изменить время блокировки (5 мин)',
        'settings_anim_05': 'Отключить анимацию (0.5x)',
        'settings_anim_0': 'Отключить анимацию (0x)',
        'settings_usb_on': 'Включить отладку USB',
        'settings_usb_off': 'Отключить отладку USB',
        'settings_android_ver': 'Показать версию Android',
        'settings_build': 'Показать сборку',
        'settings_devicename': 'Изменить имя устройства',
        'buildprop_header': 'Изменение build.prop (требуется root):',
        'buildprop_model': 'Изменить ro.product.model (введите значение)',
        'buildprop_incremental': 'Изменить ro.build.version.incremental (введите)',
        # Вкладка Логи
        'log_header': 'Логи и отладка:',
        'logcat_all': 'Показать логкат (все)',
        'logcat_errors': 'Показать логкат (ошибки)',
        'logcat_clear': 'Очистить логкат',
        'logcat_filter': 'Логкат с фильтром (введите тег)',
        'dumpsys_all': 'Дамп состояния системы',
        'dumpsys_activity': 'Дамп активности',
        'dumpsys_mem': 'Дамп памяти',
        'dumpsys_bat': 'Дамп батареи',
        'dumpsys_wifi': 'Дамп Wi-Fi',
        'dumpsys_bt': 'Дамп Bluetooth',
        'dumpsys_pkg': 'Дамп пакетов',
        'bugreport': 'Создать багрепорт (в /sdcard/bugreport.txt)',
        'bugreport_pull': 'Выгрузить багрепорт',
        'net_stats': 'Показать статистику трафика',
        # Вкладка Fastboot Extra
        'fb_extra_header': 'Дополнительные Fastboot команды:',
        'fb_unlock': 'Разблокировать загрузчик',
        'fb_lock': 'Заблокировать загрузчик',
        'fb_unlock_info': 'Информация о разблокировке',
        'fb_current_slot': 'Показать текущий слот',
        'fb_getvar_all': 'Показать все переменные',
        'fb_set_slot_a': 'Переключить слот (a)',
        'fb_set_slot_b': 'Переключить слот (b)',
        'fb_edl': 'Перезагрузить в EDL',
        'fb_fastbootd': 'Перезагрузить в Fastbootd',
        'fb_erase': 'Очистить раздел (введите имя)',
        'fb_format': 'Форматировать раздел (введите имя)',
        'fb_flash': 'Прошить образ (выберите файл)',
        'fb_boot': 'Загрузить образ без прошивки',
        # Вкладка Custom
        'custom_header': 'Введите любую ADB или Fastboot команду:',
        'custom_execute': 'Выполнить',
        # Диалоги
        'dialog_uninstall_title': 'Удаление пакета',
        'dialog_uninstall_prompt': 'Введите имя пакета (например, com.example.app):',
        'dialog_pkg_path_title': 'Путь к APK',
        'dialog_pkg_path_prompt': 'Введите имя пакета:',
        'dialog_pull_apk_title': 'Выгрузить APK',
        'dialog_pull_apk_prompt': 'Введите имя пакета:',
        'dialog_connect_ip_title': 'Подключение по IP',
        'dialog_connect_ip_prompt': 'Введите IP-адрес устройства (например, 192.168.1.10):',
        'dialog_disconnect_title': 'Отключение',
        'dialog_disconnect_prompt': 'Введите IP для отключения (или оставьте пустым для всех):',
        'dialog_edit_model_title': 'Изменить модель',
        'dialog_edit_model_prompt': 'Введите новое значение (например, Pixel 5):',
        'dialog_edit_inc_title': 'Изменить сборку',
        'dialog_edit_inc_prompt': 'Введите новое значение:',
        'dialog_logcat_filter_title': 'Фильтр логката',
        'dialog_logcat_filter_prompt': 'Введите тег (например, ActivityManager):',
        'dialog_erase_part_title': 'Очистка раздела',
        'dialog_erase_part_prompt': 'Введите имя раздела (например, cache):',
        'dialog_format_part_title': 'Форматирование раздела',
        'dialog_format_part_prompt': 'Введите имя раздела (например, userdata):',
        # Дополнительные
        'clear_data': 'Очистка данных',
        'enable_pkg': 'Включить пакет',
        'disable_pkg': 'Отключить пакет',
        'grant_perm': 'Выдать разрешение',
        'revoke_perm': 'Забрать разрешение',
        'pkg_info': 'Информация о пакете',
        'pkg_clear_prompt': 'Введите имя пакета:',
        'pkg_enable_prompt': 'Введите имя пакета:',
        'pkg_disable_prompt': 'Введите имя пакета:',
        'pkg_grant_prompt': 'Введите пакет и разрешение (например, com.app PERMISSION):',
        'pkg_revoke_prompt': 'Введите пакет и разрешение:',
        'pkg_path_prompt': 'Введите имя пакета:',
        'pkg_info_prompt': 'Введите имя пакета:',
        # About
        'menu_help': 'Справка',
        'menu_about': 'О программе',
        'about_title': 'О Phone Tools Tweaker',
        'about_text': 'Версия: {version}\nОС: {os}\nPython: {python}\nADB: {adb}\nFastboot: {fastboot}',
    },
    'en': {
        'app_title': 'Phone Tools Tweaker',
        'lang_choice': 'Choose language / Выберите язык:',
        'lang_ru': 'Russian',
        'lang_en': 'English',
        'tab_reboot': 'Modes / Power',
        'tab_info': 'Info & Status',
        'tab_flash': 'Flashing / Root',
        'tab_wipe': 'Wipe / Erase',
        'tab_backup': 'Backup / APK',
        'tab_adb_shell': 'ADB Shell',
        'tab_pm': 'Package Manager',
        'tab_screen': 'Screen / Media',
        'tab_network': 'Network',
        'tab_settings': 'Settings',
        'tab_log': 'Logs / Debug',
        'tab_fb_extra': 'Fastboot Extra',
        'tab_custom': 'Custom Command',
        'check_devices': 'Check devices (ADB / Fastboot)',
        'log_label': 'Terminal output / Log',
        'warning_tools_missing': 'WARNING: Utilities {missing} not found!',
        'scan_ports': '=== Scanning ports ===',
        'error_select_img': 'Please select an image file first!',
        'error_select_apk': 'Select an APK file!',
        'error_enter_cmd': 'Enter a command!',
        'confirm_flash': 'Flash {file} to partition {part}?',
        'confirm_erase': 'Erase partition {part}?',
        'confirm_format': 'Format partition {part}?',
        'confirm_uninstall': 'Uninstall package {pkg}?',
        'adb_commands': 'ADB Commands (Phone ON):',
        'fb_commands': 'Fastboot Commands (Bootloader mode):',
        'to_fastboot': 'To Fastboot (Bootloader)',
        'to_recovery': 'To Recovery',
        'to_edl': 'To EDL (Emergency)',
        'reboot_normal': 'Normal reboot',
        'power_off': 'Power off',
        'reboot_system': 'Reboot to System',
        'reboot_system_fb': 'Reboot to System (Fastboot)',
        'reboot_edl_fb': 'Reboot to EDL (Fastboot)',
        'to_fastbootd': 'To Fastbootd (User space)',
        'reboot_recovery_fb': 'Reboot to Recovery (Fastboot)',
        'diag_header': 'Device diagnostics:',
        'check_bootloader': 'Check bootloader status (Fastboot)',
        'getvar_all': 'Get all variables (Fastboot getvar all)',
        'get_serial': 'Show IMEI/Serial (Fastboot)',
        'get_prop_model': 'Hardware info (ADB Shell getprop)',
        'check_root': 'Check Root access (Su check)',
        'wm_size': 'Screen resolution (wm size)',
        'wm_density': 'Screen density (wm density)',
        'dumpsys_battery': 'Battery info (dumpsys battery)',
        'dumpsys_meminfo': 'Memory stats (dumpsys meminfo)',
        'getprop_all': 'List all properties (getprop)',
        'img_file_frame': 'Select image file (.img)',
        'browse_img': 'Browse...',
        'partition_mgmt': 'Partition management (Fastboot)',
        'partition_label': 'Partition:',
        'flash_selected': 'Flash selected image',
        'boot_selected': 'Boot without flashing (fastboot boot)',
        'slots_frame': 'For A/B slot devices',
        'current_slot': 'Current active slot:',
        'get_slot': 'Get slot',
        'switch_to': 'Switch to:',
        'change_slot': 'Change slot',
        'fb_extra_label': 'Additional Fastboot commands',
        'unlock_bootloader': 'Unlock bootloader (unlock)',
        'lock_bootloader': 'Lock bootloader (lock)',
        'unlock_info': 'Request unlock code info',
        'wipe_fb_header': 'Wipe and Format (Fastboot mode):',
        'erase_cache': 'Erase cache (fastboot erase cache)',
        'erase_userdata': 'Erase userdata (fastboot erase userdata)',
        'erase_system': 'Erase system (fastboot erase system)',
        'erase_vendor': 'Erase vendor (fastboot erase vendor)',
        'erase_boot': 'Erase boot (fastboot erase boot)',
        'erase_recovery': 'Erase recovery (fastboot erase recovery)',
        'format_userdata': 'Format userdata (fastboot format userdata)',
        'format_cache': 'Format cache (fastboot format cache)',
        'wipe_all': 'Wipe all partitions (wipe all) - DANGER!',
        'wipe_adb_header': 'Reset via ADB (shell):',
        'factory_reset': 'Factory reset (adb shell recovery --wipe_data)',
        'trim_caches': 'Trim app caches (adb shell pm trim-caches)',
        'backup_header': 'Backup (ADB):',
        'create_backup': 'Create full backup',
        'restore_backup': 'Restore from backup',
        'apk_header': 'Install / Uninstall APK:',
        'apk_frame': 'Select APK file',
        'install_normal': 'Install (normal)',
        'install_reinstall': 'Install (reinstall)',
        'install_sd': 'Install to SD (-s)',
        'uninstall_pkg': 'Uninstall package (enter name)',
        'list_all_pkgs': 'List all installed packages',
        'list_system_pkgs': 'List system packages',
        'list_third_pkgs': 'List third-party packages',
        'pkg_path': 'Path to APK (enter name)',
        'pull_apk': 'Pull APK from device',
        'shell_system_info': 'System info',
        'shell_df': 'Disk free space',
        'shell_free': 'Memory usage',
        'shell_top': 'Top processes',
        'shell_ps': 'List running processes',
        'shell_service': 'List services',
        'shell_netstat': 'Network statistics',
        'shell_ping': 'Ping Google',
        'shell_wifi': 'Wi-Fi info',
        'shell_bluetooth': 'Bluetooth info',
        'shell_power': 'Screen on/off',
        'shell_vol_up': 'Volume up',
        'shell_vol_down': 'Volume down',
        'shell_home': 'Home',
        'shell_back': 'Back',
        'shell_menu': 'Menu',
        'shell_screencap': 'Screenshot (shell)',
        'shell_screenrecord': 'Screen record (shell, 30 sec)',
        'shell_restart_systemui': 'Restart SystemUI',
        'shell_dns': 'Clear DNS cache',
        'pm_header': 'Package Manager (pm):',
        'pm_list_all': 'List all packages',
        'pm_list_system': 'List system packages',
        'pm_list_third': 'List third-party packages',
        'pm_list_enabled': 'List enabled packages',
        'pm_list_disabled': 'List disabled packages',
        'pm_list_perms': 'List permissions',
        'pm_clear': 'Clear package data',
        'pm_enable': 'Enable package',
        'pm_disable': 'Disable package',
        'pm_grant': 'Grant permission',
        'pm_revoke': 'Revoke permission',
        'pm_path': 'Path to APK',
        'pm_info': 'Package info',
        'pm_install': 'Install APK',
        'pm_uninstall': 'Uninstall package',
        'screen_header': 'Screen and Media:',
        'screenshot_save': 'Screenshot (save to /sdcard/screenshot.png)',
        'screenshot_pull': 'Pull screenshot to PC',
        'record_start': 'Start screen recording (30 sec, /sdcard/demo.mp4)',
        'record_pull': 'Pull screen recording',
        'set_res_1080': 'Set resolution 1080x1920',
        'reset_res': 'Reset resolution',
        'set_density_320': 'Set density 320',
        'reset_density': 'Reset density',
        'rotate_landscape': 'Rotate screen (landscape)',
        'rotate_portrait': 'Rotate screen (portrait)',
        'brightness_max': 'Increase brightness',
        'brightness_min': 'Decrease brightness (30)',
        'auto_bright_on': 'Auto brightness ON',
        'auto_bright_off': 'Auto brightness OFF',
        'network_header': 'ADB over Network:',
        'adb_tcpip': 'Switch ADB to TCP/IP (port 5555)',
        'adb_connect_ip': 'Connect to device by IP (enter IP)',
        'adb_disconnect': 'Disconnect from device',
        'show_ip': 'Show device IP address',
        'ping_device': 'Ping device (connectivity check)',
        'wifi_header': 'Wi-Fi / Bluetooth:',
        'wifi_on': 'Enable Wi-Fi',
        'wifi_off': 'Disable Wi-Fi',
        'bluetooth_on': 'Enable Bluetooth',
        'bluetooth_off': 'Disable Bluetooth',
        'settings_header': 'System settings (settings):',
        'settings_list_global': 'Show all global settings',
        'settings_list_secure': 'Show secure settings',
        'settings_list_system': 'Show system settings',
        'settings_timeout_30': 'Set screen timeout to 30 sec',
        'settings_timeout_5min': 'Set screen timeout to 5 min',
        'settings_anim_05': 'Set animation scale 0.5x',
        'settings_anim_0': 'Set animation scale 0x',
        'settings_usb_on': 'Enable USB debugging',
        'settings_usb_off': 'Disable USB debugging',
        'settings_android_ver': 'Show Android version',
        'settings_build': 'Show build number',
        'settings_devicename': 'Change device name',
        'buildprop_header': 'Edit build.prop (root required):',
        'buildprop_model': 'Change ro.product.model (enter value)',
        'buildprop_incremental': 'Change ro.build.version.incremental (enter value)',
        'log_header': 'Logs and Debugging:',
        'logcat_all': 'Show logcat (all)',
        'logcat_errors': 'Show logcat (errors)',
        'logcat_clear': 'Clear logcat',
        'logcat_filter': 'Logcat with filter (enter tag)',
        'dumpsys_all': 'Dump system state',
        'dumpsys_activity': 'Dump activity',
        'dumpsys_mem': 'Dump memory',
        'dumpsys_bat': 'Dump battery',
        'dumpsys_wifi': 'Dump Wi-Fi',
        'dumpsys_bt': 'Dump Bluetooth',
        'dumpsys_pkg': 'Dump packages',
        'bugreport': 'Create bugreport (in /sdcard/bugreport.txt)',
        'bugreport_pull': 'Pull bugreport',
        'net_stats': 'Show traffic statistics',
        'fb_extra_header': 'Additional Fastboot commands:',
        'fb_unlock': 'Unlock bootloader',
        'fb_lock': 'Lock bootloader',
        'fb_unlock_info': 'Unlock info',
        'fb_current_slot': 'Show current slot',
        'fb_getvar_all': 'Show all variables',
        'fb_set_slot_a': 'Switch slot (a)',
        'fb_set_slot_b': 'Switch slot (b)',
        'fb_edl': 'Reboot to EDL',
        'fb_fastbootd': 'Reboot to Fastbootd',
        'fb_erase': 'Erase partition (enter name)',
        'fb_format': 'Format partition (enter name)',
        'fb_flash': 'Flash image (select file)',
        'fb_boot': 'Boot image without flashing',
        'custom_header': 'Enter any ADB or Fastboot command:',
        'custom_execute': 'Execute',
        'dialog_uninstall_title': 'Uninstall package',
        'dialog_uninstall_prompt': 'Enter package name (e.g., com.example.app):',
        'dialog_pkg_path_title': 'APK Path',
        'dialog_pkg_path_prompt': 'Enter package name:',
        'dialog_pull_apk_title': 'Pull APK',
        'dialog_pull_apk_prompt': 'Enter package name:',
        'dialog_connect_ip_title': 'Connect by IP',
        'dialog_connect_ip_prompt': 'Enter device IP address (e.g., 192.168.1.10):',
        'dialog_disconnect_title': 'Disconnect',
        'dialog_disconnect_prompt': 'Enter IP to disconnect (or leave empty for all):',
        'dialog_edit_model_title': 'Edit model',
        'dialog_edit_model_prompt': 'Enter new value (e.g., Pixel 5):',
        'dialog_edit_inc_title': 'Edit build incremental',
        'dialog_edit_inc_prompt': 'Enter new value:',
        'dialog_logcat_filter_title': 'Logcat filter',
        'dialog_logcat_filter_prompt': 'Enter tag (e.g., ActivityManager):',
        'dialog_erase_part_title': 'Erase partition',
        'dialog_erase_part_prompt': 'Enter partition name (e.g., cache):',
        'dialog_format_part_title': 'Format partition',
        'dialog_format_part_prompt': 'Enter partition name (e.g., userdata):',
        'clear_data': 'Clear data',
        'enable_pkg': 'Enable package',
        'disable_pkg': 'Disable package',
        'grant_perm': 'Grant permission',
        'revoke_perm': 'Revoke permission',
        'pkg_info': 'Package info',
        'pkg_clear_prompt': 'Enter package name:',
        'pkg_enable_prompt': 'Enter package name:',
        'pkg_disable_prompt': 'Enter package name:',
        'pkg_grant_prompt': 'Enter package and permission (e.g., com.app PERMISSION):',
        'pkg_revoke_prompt': 'Enter package and permission:',
        'pkg_path_prompt': 'Enter package name:',
        'pkg_info_prompt': 'Enter package name:',
        'menu_help': 'Help',
        'menu_about': 'About',
        'about_title': 'About Phone Tools Tweaker',
        'about_text': 'Version: {version}\nOS: {os}\nPython: {python}\nADB: {adb}\nFastboot: {fastboot}',
    }
}

# --------------------- Вспомогательные классы ---------------------
class LogManager:
    """Дублирует вывод в текстовый виджет и в файл. Файл сохраняется в каталоге конфигурации."""
    def __init__(self, text_widget, config_dir, filename='phone_tools_tweaker.log'):
        self.text = text_widget
        self.filename = os.path.join(config_dir, filename)
        try:
            self.file = open(self.filename, 'a', encoding='utf-8')
        except Exception:
            self.file = None

    def write(self, message, end='\n'):
        self.text.insert(tk.END, message + end)
        self.text.see(tk.END)
        if self.file:
            try:
                self.file.write(message + end)
                self.file.flush()
            except Exception:
                pass

    def close(self):
        if self.file:
            self.file.close()
            self.file = None


class CommandTask(threading.Thread):
    """Фоновое выполнение команды с возможностью отмены."""
    def __init__(self, command_args, shell=False, callback=None):
        super().__init__(daemon=True)
        self.command_args = command_args
        self.shell = shell
        self.callback = callback
        self.output_queue = queue.Queue()
        self.proc = None
        self._cancelled = False

    def run(self):
        try:
            self.proc = subprocess.Popen(
                self.command_args,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                shell=self.shell,
                bufsize=1
            )
            for line in self.proc.stdout:
                if self._cancelled:
                    break
                self.output_queue.put(line)
            self.proc.stdout.close()
            returncode = self.proc.wait()
            if not self._cancelled:
                self.output_queue.put(f"\n[Процесс завершён, код {returncode}]\n")
        except Exception as e:
            self.output_queue.put(f"[Ошибка выполнения] {str(e)}\n")
        finally:
            self.output_queue.put(None)

    def cancel(self):
        self._cancelled = True
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            # Даём время на завершение, затем убиваем
            def kill_process():
                if self.proc and self.proc.poll() is None:
                    self.proc.kill()
            timer = threading.Timer(2.0, kill_process)
            timer.daemon = True
            timer.start()

    def get_line(self):
        try:
            return self.output_queue.get_nowait()
        except queue.Empty:
            return None


class SequenceCommandTask(threading.Thread):
    """Выполняет несколько команд последовательно и собирает вывод."""
    def __init__(self, command_list, callback=None):
        super().__init__(daemon=True)
        self.command_list = command_list  # список списков аргументов
        self.callback = callback
        self.output_queue = queue.Queue()
        self._cancelled = False
        self.proc = None

    def run(self):
        for cmd_args in self.command_list:
            if self._cancelled:
                break
            cmd_str = ' '.join(shlex.quote(a) for a in cmd_args)
            self.output_queue.put(f"\n> {cmd_str}\n")
            try:
                self.proc = subprocess.Popen(
                    cmd_args,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1
                )
                for line in self.proc.stdout:
                    if self._cancelled:
                        self.proc.terminate()
                        break
                    self.output_queue.put(line)
                self.proc.stdout.close()
                returncode = self.proc.wait()
                if not self._cancelled:
                    self.output_queue.put(f"[Команда завершена, код {returncode}]\n")
            except Exception as e:
                self.output_queue.put(f"[Ошибка выполнения] {str(e)}\n")
        self.output_queue.put(None)

    def cancel(self):
        self._cancelled = True
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            def kill_process():
                if self.proc and self.proc.poll() is None:
                    self.proc.kill()
            timer = threading.Timer(2.0, kill_process)
            timer.daemon = True
            timer.start()

    def get_line(self):
        try:
            return self.output_queue.get_nowait()
        except queue.Empty:
            return None


class ScrollableFrame(ttk.Frame):
    """Фрейм с вертикальной прокруткой."""
    def __init__(self, container, *args, **kwargs):
        super().__init__(container, *args, **kwargs)
        canvas = tk.Canvas(self, bg='#1e1e1e', highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")


class LanguageManager:
    """Загрузка/сохранение языка в AppData/XDG_CONFIG_HOME."""
    def __init__(self):
        self.config_dir = self._get_config_dir()
        self.config_file = os.path.join(self.config_dir, 'config.ini')
        self.lang = 'ru'
        self.load()

    def _get_config_dir(self):
        if sys.platform == 'win32':
            base = os.environ.get('APPDATA', os.path.expanduser('~'))
        else:
            base = os.environ.get('XDG_CONFIG_HOME', os.path.join(os.path.expanduser('~'), '.config'))
        path = os.path.join(base, 'PhoneToolsTweaker')
        try:
            os.makedirs(path, exist_ok=True)
        except OSError:
            path = os.path.dirname(os.path.abspath(__file__))
        return path

    def load(self):
        config = configparser.ConfigParser()
        if os.path.exists(self.config_file):
            try:
                config.read(self.config_file, encoding='utf-8')
                lang = config.get('Settings', 'language', fallback='ru')
                if lang in LANGUAGES:
                    self.lang = lang
                else:
                    self.lang = 'ru'
            except (configparser.Error, UnicodeDecodeError):
                self.lang = 'ru'
        else:
            self.lang = self.ask_language()
            self.save()

    def save(self):
        config = configparser.ConfigParser()
        config['Settings'] = {'language': self.lang}
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                config.write(f)
        except OSError:
            pass

    def ask_language(self):
        root = tk.Tk()
        root.title('Language Selection')
        root.geometry('300x150')
        root.resizable(False, False)
        root.eval('tk::PlaceWindow . center')

        tk.Label(root, text=LANGUAGES['ru']['lang_choice'], font=('Arial', 12)).pack(pady=10)
        var = tk.StringVar(value='ru')
        frame = tk.Frame(root)
        frame.pack(pady=10)
        tk.Radiobutton(frame, text='Русский', variable=var, value='ru').pack(side='left', padx=10)
        tk.Radiobutton(frame, text='English', variable=var, value='en').pack(side='left', padx=10)
        tk.Button(root, text='OK', command=root.destroy, width=10).pack(pady=10)
        root.mainloop()
        return var.get()


# --------------------- Основное приложение ---------------------
class PhoneToolsTweakerApp:
    def __init__(self, root):
        self.root = root
        self.lang_manager = LanguageManager()
        self.lang = self.lang_manager.lang
        self.strings = LANGUAGES[self.lang]

        self.version = "1.0"
        self.root.title(f"{self.strings['app_title']} v{self.version}")

        # Иконка (кроссплатформенная)
        try:
            if sys.platform == 'win32':
                self.root.iconbitmap('app.ico')
            else:
                # Попытаться загрузить PNG (если есть)
                if os.path.exists('app.png'):
                    img = tk.PhotoImage(file='app.png')
                    self.root.iconphoto(True, img)
        except Exception:
            pass

        self.root.geometry("1050x800")
        self.root.resizable(True, True)
        self.root.configure(bg='#1e1e1e')

        self.logger = None  # будет создан после создания виджета лога
        self.setup_environment()

        # Переменные
        self.img_file_path = tk.StringVar()
        self.apk_file_path = tk.StringVar()
        self.backup_path = tk.StringVar(value="backup.ab")
        self.selected_partition = tk.StringVar(value="boot")
        self.slot_var = tk.StringVar(value="a")
        self.custom_command = tk.StringVar()

        self.current_task = None
        self.after_id = None

        self.create_widgets()
        self.check_tools_silently()

    def setup_environment(self):
        # Определяем базовую директорию (для PyInstaller)
        if getattr(sys, 'frozen', False):
            base_dir = sys._MEIPASS
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))

        tools_dir = os.path.join(base_dir, 'tools')

        # Сначала проверяем наличие adb и fastboot в системе
        adb_path = shutil.which('adb')
        fastboot_path = shutil.which('fastboot')
        if adb_path and fastboot_path:
            self.log(f"[OK] ADB found: {adb_path}")
            self.log(f"[OK] Fastboot found: {fastboot_path}")
            # Не добавляем tools в PATH, используем системные
        else:
            # Ищем в папке tools
            if sys.platform == 'win32':
                adb_exe = 'adb.exe'
                fastboot_exe = 'fastboot.exe'
            else:
                adb_exe = 'adb'
                fastboot_exe = 'fastboot'

            adb_tool = os.path.join(tools_dir, adb_exe)
            fastboot_tool = os.path.join(tools_dir, fastboot_exe)

            if os.path.isfile(adb_tool) and os.path.isfile(fastboot_tool):
                # Добавляем tools в начало PATH
                os.environ["PATH"] = tools_dir + os.pathsep + os.environ["PATH"]
                self.log(f"[OK] Using tools from: {tools_dir}")
            else:
                self.log("[WARN] Neither system nor tools folder contain adb/fastboot. Commands may fail.")

        # Дополнительно проверим наличие через which после изменения PATH
        adb_path = shutil.which('adb')
        fastboot_path = shutil.which('fastboot')
        if adb_path:
            self.log(f"[INFO] ADB resolved to: {adb_path}")
        else:
            self.log("[ERROR] ADB not found in PATH or tools.")
        if fastboot_path:
            self.log(f"[INFO] Fastboot resolved to: {fastboot_path}")
        else:
            self.log("[ERROR] Fastboot not found in PATH or tools.")

    # ---------- Логирование ----------
    def log(self, message, end='\n'):
        if self.logger:
            self.logger.write(message, end)

    # ---------- Асинхронное выполнение ----------
    def run_task(self, command_args, shell=False, callback=None):
        if self.current_task and self.current_task.is_alive():
            self.log("[Занято] Дождитесь завершения предыдущей операции.")
            return
        if shell:
            cmd_str = command_args if isinstance(command_args, str) else ' '.join(command_args)
        else:
            cmd_str = ' '.join(shlex.quote(a) for a in command_args)
        self.log(f"\n> {cmd_str}")
        self.start_progress()
        self.current_task = CommandTask(command_args, shell=shell, callback=callback)
        self.current_task.start()
        self.poll_task_output()

    def run_sequence(self, command_list, callback=None):
        """Выполнить список команд последовательно."""
        if self.current_task and self.current_task.is_alive():
            self.log("[Занято] Дождитесь завершения предыдущей операции.")
            return
        self.log("\n> Запуск последовательности команд...")
        self.start_progress()
        self.current_task = SequenceCommandTask(command_list, callback=callback)
        self.current_task.start()
        self.poll_task_output()

    def poll_task_output(self):
        if self.current_task is None:
            self.stop_progress()
            return
        while True:
            line = self.current_task.get_line()
            if line is None:
                self.log("[Операция завершена]")
                self.stop_progress()
                if self.current_task.callback:
                    self.root.after(0, self.current_task.callback)
                self.current_task = None
                return
            else:
                self.log(line.rstrip('\r\n'))
        self.after_id = self.root.after(100, self.poll_task_output)

    def cancel_task(self):
        if self.current_task and self.current_task.is_alive():
            self.current_task.cancel()
            self.log("[Отменено пользователем]")
            self.stop_progress()
            self.current_task = None

    def start_progress(self):
        if hasattr(self, 'progress'):
            self.progress.start(10)
        if hasattr(self, 'stop_btn'):
            self.stop_btn.config(state=tk.NORMAL)

    def stop_progress(self):
        if hasattr(self, 'progress'):
            self.progress.stop()
        if hasattr(self, 'stop_btn'):
            self.stop_btn.config(state=tk.DISABLED)
        if self.after_id:
            self.root.after_cancel(self.after_id)
            self.after_id = None

    # ---------- Проверка инструментов ----------
    def check_tools_silently(self):
        adb_path = shutil.which('adb')
        fastboot_path = shutil.which('fastboot')
        if not adb_path or not fastboot_path:
            missing = []
            if not adb_path:
                missing.append('adb')
            if not fastboot_path:
                missing.append('fastboot')
            msg = self.strings['warning_tools_missing'].format(missing=', '.join(missing))
            self.log(msg)
        else:
            self.log("[OK] ADB and Fastboot are available.")

    # ---------- Фабрика кнопок ----------
    def make_button(self, parent, text, command, **kwargs):
        defaults = {'bg': '#3c3c3c', 'fg': 'white', 'relief': 'flat'}
        for key, value in defaults.items():
            kwargs.setdefault(key, value)
        return tk.Button(parent, text=text, command=command, **kwargs)

    # ---------- Смена языка (кроссплатформенный перезапуск) ----------
    def change_language(self, lang_code):
        if lang_code == self.lang_manager.lang:
            return
        self.lang_manager.lang = lang_code
        self.lang_manager.save()
        # Завершаем текущий процесс и запускаем новый
        self.root.quit()
        subprocess.Popen([sys.executable] + sys.argv)
        sys.exit(0)

    # ---------- Создание GUI ----------
    def create_widgets(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TNotebook', background='#2d2d2d', borderwidth=0)
        style.configure('TNotebook.Tab', background='#3c3c3c', foreground='white', padding=[12, 4])
        style.map('TNotebook.Tab',
                  background=[('selected', '#0078d7')],
                  foreground=[('selected', 'white')])
        style.configure('TFrame', background='#1e1e1e')
        style.configure('TLabel', background='#1e1e1e', foreground='white')
        style.configure('TButton', background='#0078d7', foreground='white', borderwidth=1)
        style.map('TButton', background=[('active', '#005a9e')])

        # Меню
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        lang_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Language", menu=lang_menu)
        lang_menu.add_command(label="Русский", command=lambda: self.change_language('ru'))
        lang_menu.add_command(label="English", command=lambda: self.change_language('en'))

        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label=self.strings['menu_help'], menu=help_menu)
        help_menu.add_command(label=self.strings['menu_about'], command=self.show_about)

        # Верхняя панель
        top_frame = tk.Frame(self.root, bg='#2d2d2d', pady=5)
        top_frame.pack(fill="x", side="top")
        self.make_button(top_frame, self.strings['check_devices'], self.check_devices,
                         font=("Arial", 10, "bold"), bg='#0078d7').pack(side="left", padx=10)

        # Блокнот вкладок
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=5)

        # Создание вкладок
        self.create_tab_reboot()
        self.create_tab_info()
        self.create_tab_flash()
        self.create_tab_wipe()
        self.create_tab_apps_backup()
        self.create_tab_adb_shell()
        self.create_tab_package_manager()
        self.create_tab_screen_media()
        self.create_tab_network()
        self.create_tab_settings()
        self.create_tab_log_debug()
        self.create_tab_fastboot_extra()
        self.create_tab_custom_command()

        # Лог-панель
        bot_frame = tk.LabelFrame(self.root, text=" " + self.strings['log_label'] + " ",
                                  font=("Arial", 9, "bold"), bg='#2d2d2d', fg='white',
                                  relief='groove', bd=2)
        bot_frame.pack(fill="both", expand=False, height=250, padx=10, pady=5)

        self.log_text = tk.Text(bot_frame, height=10, wrap="word",
                                bg='#0c0c0c', fg='#00ff00',
                                font=("monospace", 10), insertbackground='white', relief='flat')
        self.log_text.pack(fill="both", expand=True, side="left", padx=5, pady=5)

        scrollbar = tk.Scrollbar(bot_frame, command=self.log_text.yview, bg='#2d2d2d')
        scrollbar.pack(side="right", fill="y")
        self.log_text.config(yscrollcommand=scrollbar.set)

        self.logger = LogManager(self.log_text, self.lang_manager.config_dir)

        self.progress = ttk.Progressbar(bot_frame, mode='indeterminate', length=200)
        self.progress.pack(pady=(0, 5))
        self.stop_btn = tk.Button(bot_frame, text="⏹ Стоп", command=self.cancel_task,
                                  bg='#d9534f', fg='white', relief='flat', state=tk.DISABLED)
        self.stop_btn.pack(pady=(0, 5))

    def show_about(self):
        adb_path = shutil.which('adb') or 'не найден'
        fastboot_path = shutil.which('fastboot') or 'не найден'
        os_info = sys.platform
        python_ver = sys.version.split()[0]
        text = self.strings['about_text'].format(
            version=self.version,
            os=os_info,
            python=python_ver,
            adb=adb_path,
            fastboot=fastboot_path
        )
        messagebox.showinfo(self.strings['about_title'], text)

    def check_devices(self):
        self.log("\n" + self.strings['scan_ports'])
        self.run_task(['adb', 'devices'])
        self.run_task(['fastboot', 'devices'])

    # ---------- Вкладки (все полностью) ----------
    def create_tab_reboot(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text=self.strings['tab_reboot'])
        sf = ScrollableFrame(tab)
        sf.pack(fill="both", expand=True)
        f = sf.scrollable_frame

        tk.Label(f, text=self.strings['adb_commands'], font=("Arial", 10, "bold"),
                 bg='#1e1e1e', fg='white').grid(row=0, column=0, columnspan=3, sticky="w", padx=10, pady=10)

        adb_buttons = [
            (self.strings['to_fastboot'], ['adb', 'reboot', 'bootloader']),
            (self.strings['to_recovery'], ['adb', 'reboot', 'recovery']),
            (self.strings['to_edl'], ['adb', 'reboot', 'edl']),
            (self.strings['reboot_normal'], ['adb', 'reboot']),
            (self.strings['power_off'], ['adb', 'shell', 'reboot', '-p']),
            (self.strings['reboot_system'], ['adb', 'reboot', 'system']),
        ]
        for i, (text, cmd) in enumerate(adb_buttons):
            col = i % 3
            row = 1 + i // 3
            self.make_button(f, text, lambda c=cmd: self.run_task(c), width=28).grid(row=row, column=col, padx=10, pady=5)

        tk.Label(f, text=self.strings['fb_commands'], font=("Arial", 10, "bold"),
                 bg='#1e1e1e', fg='white').grid(row=3, column=0, columnspan=3, sticky="w", padx=10, pady=15)

        fb_buttons = [
            (self.strings['reboot_system_fb'], ['fastboot', 'reboot']),
            (self.strings['reboot_edl_fb'], ['fastboot', 'oem', 'edl']),
            (self.strings['to_fastbootd'], ['fastboot', 'reboot', 'fastboot']),
            (self.strings['reboot_recovery_fb'], ['fastboot', 'reboot', 'recovery']),
        ]
        for i, (text, cmd) in enumerate(fb_buttons):
            col = i % 3
            row = 4 + i // 3
            color = '#fff9c4' if 'System' in text and 'fastboot reboot' in str(cmd) else '#3c3c3c'
            fg = 'black' if color == '#fff9c4' else 'white'
            self.make_button(f, text, lambda c=cmd: self.run_task(c), width=28, bg=color, fg=fg).grid(row=row, column=col, padx=10, pady=5)

    def create_tab_info(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text=self.strings['tab_info'])
        sf = ScrollableFrame(tab)
        sf.pack(fill="both", expand=True)
        f = sf.scrollable_frame

        tk.Label(f, text=self.strings['diag_header'], font=("Arial", 10, "bold"),
                 bg='#1e1e1e', fg='white').pack(anchor="w", padx=10, pady=10)

        info_buttons = [
            (self.strings['check_bootloader'], ['fastboot', 'oem', 'device-info']),
            (self.strings['getvar_all'], ['fastboot', 'getvar', 'all']),
            (self.strings['get_serial'], ['fastboot', 'getvar', 'serialno']),
            (self.strings['get_prop_model'], ['adb', 'shell', 'getprop', 'ro.product.model']),
            (self.strings['check_root'], ['adb', 'shell', 'su', '-c', 'id']),
            (self.strings['wm_size'], ['adb', 'shell', 'wm', 'size']),
            (self.strings['wm_density'], ['adb', 'shell', 'wm', 'density']),
            (self.strings['dumpsys_battery'], ['adb', 'shell', 'dumpsys', 'battery']),
            (self.strings['dumpsys_meminfo'], ['adb', 'shell', 'dumpsys', 'meminfo']),
            (self.strings['getprop_all'], ['adb', 'shell', 'getprop']),
        ]
        for text, cmd in info_buttons:
            self.make_button(f, text, lambda c=cmd: self.run_task(c), width=55, anchor="w").pack(padx=20, pady=4, anchor="w")

    def create_tab_flash(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text=self.strings['tab_flash'])
        sf = ScrollableFrame(tab)
        sf.pack(fill="both", expand=True)
        f = sf.scrollable_frame

        frame_file = tk.LabelFrame(f, text=" " + self.strings['img_file_frame'] + " ",
                                   bg='#2d2d2d', fg='white', relief='groove', bd=2)
        frame_file.pack(fill="x", padx=10, pady=10)
        tk.Entry(frame_file, textvariable=self.img_file_path, width=65,
                 bg='#3c3c3c', fg='white', insertbackground='white').pack(side="left", padx=5, pady=5)
        tk.Button(frame_file, text=self.strings['browse_img'],
                  command=self.browse_img_file,
                  bg='#0078d7', fg='white', relief='flat').pack(side="left", padx=5)

        frame_part = tk.LabelFrame(f, text=" " + self.strings['partition_mgmt'] + " ",
                                   bg='#2d2d2d', fg='white', relief='groove', bd=2)
        frame_part.pack(fill="x", padx=10, pady=5)
        tk.Label(frame_part, text=self.strings['partition_label'] + ":",
                 bg='#2d2d2d', fg='white').grid(row=0, column=0, padx=5, pady=5)
        ttk.Combobox(frame_part, textvariable=self.selected_partition,
                     values=["boot", "recovery", "vbmeta", "system", "vendor", "userdata",
                             "dtbo", "abl", "xbl", "tz", "hyp", "modem"]).grid(row=0, column=1, padx=5, pady=5)
        tk.Button(frame_part, text=self.strings['flash_selected'],
                  command=self.flash_selected_image,
                  bg='#0078d7', fg='white', relief='flat').grid(row=0, column=2, padx=15, pady=5)
        tk.Button(frame_part, text=self.strings['boot_selected'],
                  command=self.boot_selected_image,
                  bg='#3c3c3c', fg='white', relief='flat').grid(row=0, column=3, padx=5, pady=5)

        frame_slots = tk.LabelFrame(f, text=" " + self.strings['slots_frame'] + " ",
                                    bg='#2d2d2d', fg='white', relief='groove', bd=2)
        frame_slots.pack(fill="x", padx=10, pady=10)
        tk.Label(frame_slots, text=self.strings['current_slot'],
                 bg='#2d2d2d', fg='white').pack(side="left", padx=5)
        tk.Button(frame_slots, text=self.strings['get_slot'],
                  command=lambda: self.run_task(['fastboot', 'getvar', 'current-slot']),
                  bg='#3c3c3c', fg='white', relief='flat').pack(side="left", padx=5)
        tk.Label(frame_slots, text="  " + self.strings['switch_to'],
                 bg='#2d2d2d', fg='white').pack(side="left", padx=5)
        ttk.Combobox(frame_slots, textvariable=self.slot_var, values=["a", "b"], width=5).pack(side="left", padx=5)
        tk.Button(frame_slots, text=self.strings['change_slot'],
                  command=lambda: self.run_task(['fastboot', '--set-active=' + self.slot_var.get()]),
                  bg='#3c3c3c', fg='white', relief='flat').pack(side="left", padx=5)

        frame_extra = tk.LabelFrame(f, text=" " + self.strings['fb_extra_label'] + " ",
                                    bg='#2d2d2d', fg='white', relief='groove', bd=2)
        frame_extra.pack(fill="x", padx=10, pady=10)
        tk.Button(frame_extra, text=self.strings['unlock_bootloader'], width=30,
                  command=lambda: self.run_task(['fastboot', 'oem', 'unlock']),
                  bg='#3c3c3c', fg='white', relief='flat').pack(side="left", padx=5)
        tk.Button(frame_extra, text=self.strings['lock_bootloader'], width=30,
                  command=lambda: self.run_task(['fastboot', 'oem', 'lock']),
                  bg='#3c3c3c', fg='white', relief='flat').pack(side="left", padx=5)
        tk.Button(frame_extra, text=self.strings['unlock_info'], width=30,
                  command=lambda: self.run_task(['fastboot', 'oem', 'unlock-info']),
                  bg='#3c3c3c', fg='white', relief='flat').pack(side="left", padx=5)

    def browse_img_file(self):
        f = filedialog.askopenfilename(filetypes=[("Image files", "*.img"), ("All files", "*.*")])
        if f:
            self.img_file_path.set(f)

    def flash_selected_image(self):
        path = self.img_file_path.get()
        part = self.selected_partition.get()
        if not path:
            messagebox.showwarning("Error", self.strings['error_select_img'])
            return
        if messagebox.askyesno("Confirm",
                               self.strings['confirm_flash'].format(file=os.path.basename(path), part=part.upper())):
            self.run_task(['fastboot', 'flash', part, path])

    def boot_selected_image(self):
        path = self.img_file_path.get()
        if not path:
            messagebox.showwarning("Error", self.strings['error_select_img'])
            return
        self.run_task(['fastboot', 'boot', path])

    def create_tab_wipe(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text=self.strings['tab_wipe'])
        sf = ScrollableFrame(tab)
        sf.pack(fill="both", expand=True)
        f = sf.scrollable_frame

        tk.Label(f, text=self.strings['wipe_fb_header'], font=("Arial", 10, "bold"),
                 bg='#1e1e1e', fg='white').pack(anchor="w", padx=10, pady=10)

        wipe_cmds = [
            (self.strings['erase_cache'], ['fastboot', 'erase', 'cache']),
            (self.strings['erase_userdata'], ['fastboot', 'erase', 'userdata']),
            (self.strings['erase_system'], ['fastboot', 'erase', 'system']),
            (self.strings['erase_vendor'], ['fastboot', 'erase', 'vendor']),
            (self.strings['erase_boot'], ['fastboot', 'erase', 'boot']),
            (self.strings['erase_recovery'], ['fastboot', 'erase', 'recovery']),
            (self.strings['format_userdata'], ['fastboot', 'format', 'userdata']),
            (self.strings['format_cache'], ['fastboot', 'format', 'cache']),
            # wipe_all заменяем на последовательный вызов
            (self.strings['wipe_all'], self.wipe_all_sequence),
        ]
        for text, cmd in wipe_cmds:
            color = '#ffcdd2' if 'wipe all' in text.lower() else '#3c3c3c'
            fg_color = 'black' if color == '#ffcdd2' else 'white'
            if callable(cmd):
                action = cmd
            else:
                action = lambda c=cmd: self.run_task(c)
            self.make_button(f, text, action, width=55, anchor="w",
                             bg=color, fg=fg_color).pack(padx=20, pady=5, anchor="w")

        tk.Label(f, text=self.strings['wipe_adb_header'], font=("Arial", 10, "bold"),
                 bg='#1e1e1e', fg='white').pack(anchor="w", padx=10, pady=10)
        self.make_button(f, self.strings['factory_reset'],
                         lambda: self.run_task(['adb', 'shell', 'recovery', '--wipe_data']),
                         width=55, anchor="w").pack(padx=20, pady=5, anchor="w")
        self.make_button(f, self.strings['trim_caches'],
                         lambda: self.run_task(['adb', 'shell', 'pm', 'trim-caches', '999G']),
                         width=55, anchor="w").pack(padx=20, pady=5, anchor="w")

    def wipe_all_sequence(self):
        if messagebox.askyesno("Confirm", self.strings['confirm_erase'].format(part="system, userdata, cache")):
            self.run_sequence([
                ['fastboot', 'erase', 'system'],
                ['fastboot', 'erase', 'userdata'],
                ['fastboot', 'erase', 'cache']
            ])

    def create_tab_apps_backup(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text=self.strings['tab_backup'])
        sf = ScrollableFrame(tab)
        sf.pack(fill="both", expand=True)
        f = sf.scrollable_frame

        tk.Label(f, text=self.strings['backup_header'], font=("Arial", 10, "bold"),
                 bg='#1e1e1e', fg='white').grid(row=0, column=0, columnspan=3, sticky="w", padx=10, pady=10)
        tk.Entry(f, textvariable=self.backup_path, width=30,
                 bg='#3c3c3c', fg='white', insertbackground='white').grid(row=1, column=0, padx=5, pady=5)
        self.make_button(f, self.strings['create_backup'],
                         lambda: self.run_task(['adb', 'backup', '-apk', '-shared', '-all', '-system', '-f', self.backup_path.get()]),
                         bg='#0078d7', fg='white').grid(row=1, column=1, padx=5, pady=5)
        self.make_button(f, self.strings['restore_backup'],
                         lambda: self.run_task(['adb', 'restore', self.backup_path.get()]),
                         bg='#3c3c3c', fg='white').grid(row=1, column=2, padx=5, pady=5)

        tk.Label(f, text=self.strings['apk_header'], font=("Arial", 10, "bold"),
                 bg='#1e1e1e', fg='white').grid(row=2, column=0, columnspan=3, sticky="w", padx=10, pady=10)
        frame_apk = tk.LabelFrame(f, text=" " + self.strings['apk_frame'] + " ",
                                  bg='#2d2d2d', fg='white', relief='groove', bd=2)
        frame_apk.grid(row=3, column=0, columnspan=3, padx=10, pady=5, sticky="ew")
        tk.Entry(frame_apk, textvariable=self.apk_file_path, width=50,
                 bg='#3c3c3c', fg='white', insertbackground='white').pack(side="left", padx=5)
        tk.Button(frame_apk, text=self.strings['browse_img'],
                  command=self.browse_apk_file,
                  bg='#0078d7', fg='white', relief='flat').pack(side="left", padx=5)
        self.make_button(frame_apk, self.strings['install_normal'], self.install_apk).pack(side="left", padx=5)
        self.make_button(frame_apk, self.strings['install_reinstall'],
                         lambda: self.run_task(['adb', 'install', '-r', self.apk_file_path.get()])).pack(side="left", padx=5)
        self.make_button(frame_apk, self.strings['install_sd'],
                         lambda: self.run_task(['adb', 'install', '-s', self.apk_file_path.get()])).pack(side="left", padx=5)
        self.make_button(frame_apk, self.strings['uninstall_pkg'], self.uninstall_package).pack(side="left", padx=5)

        self.make_button(f, self.strings['list_all_pkgs'],
                         lambda: self.run_task(['adb', 'shell', 'pm', 'list', 'packages']),
                         width=30).grid(row=4, column=0, padx=5, pady=5)
        self.make_button(f, self.strings['list_system_pkgs'],
                         lambda: self.run_task(['adb', 'shell', 'pm', 'list', 'packages', '-s']),
                         width=30).grid(row=4, column=1, padx=5, pady=5)
        self.make_button(f, self.strings['list_third_pkgs'],
                         lambda: self.run_task(['adb', 'shell', 'pm', 'list', 'packages', '-3']),
                         width=30).grid(row=4, column=2, padx=5, pady=5)
        self.make_button(f, self.strings['pkg_path'], self.get_package_path,
                         width=30).grid(row=5, column=0, padx=5, pady=5)
        self.make_button(f, self.strings['pull_apk'], self.pull_apk,
                         width=30).grid(row=5, column=1, padx=5, pady=5)

    def browse_apk_file(self):
        f = filedialog.askopenfilename(filetypes=[("APK files", "*.apk"), ("All files", "*.*")])
        if f:
            self.apk_file_path.set(f)

    def install_apk(self):
        path = self.apk_file_path.get()
        if not path:
            messagebox.showwarning("Error", self.strings['error_select_apk'])
            return
        self.run_task(['adb', 'install', path])

    def uninstall_package(self):
        pkg = simpledialog.askstring(
            self.strings['dialog_uninstall_title'],
            self.strings['dialog_uninstall_prompt']
        )
        if pkg:
            if messagebox.askyesno("Confirm", self.strings['confirm_uninstall'].format(pkg=pkg)):
                self.run_task(['adb', 'uninstall', pkg])

    def get_package_path(self):
        pkg = simpledialog.askstring(
            self.strings['dialog_pkg_path_title'],
            self.strings['dialog_pkg_path_prompt']
        )
        if pkg:
            self.run_task(['adb', 'shell', 'pm', 'path', pkg])

    def pull_apk(self):
        pkg = simpledialog.askstring(
            self.strings['dialog_pull_apk_title'],
            self.strings['dialog_pull_apk_prompt']
        )
        if not pkg:
            return
        def on_path_output():
            self.log("Используйте 'adb pull <путь> .', путь можно скопировать выше.")
        self.run_task(['adb', 'shell', 'pm', 'path', pkg], callback=on_path_output)

    def create_tab_adb_shell(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text=self.strings['tab_adb_shell'])
        sf = ScrollableFrame(tab)
        sf.pack(fill="both", expand=True)
        f = sf.scrollable_frame

        shell_cmds = [
            (self.strings['shell_system_info'], ['adb', 'shell', 'getprop']),
            (self.strings['shell_df'], ['adb', 'shell', 'df', '-h']),
            (self.strings['shell_free'], ['adb', 'shell', 'free', '-m']),
            (self.strings['shell_top'], ['adb', 'shell', 'top', '-n', '1']),
            (self.strings['shell_ps'], ['adb', 'shell', 'ps']),
            (self.strings['shell_service'], ['adb', 'shell', 'service', 'list']),
            (self.strings['shell_netstat'], ['adb', 'shell', 'netstat']),
            (self.strings['shell_ping'], ['adb', 'shell', 'ping', '-c', '4', '8.8.8.8']),  # исправлено
            (self.strings['shell_wifi'], ['adb', 'shell', 'dumpsys', 'wifi']),
            (self.strings['shell_bluetooth'], ['adb', 'shell', 'dumpsys', 'bluetooth_manager']),
            (self.strings['shell_power'], ['adb', 'shell', 'input', 'keyevent', 'KEYCODE_POWER']),
            (self.strings['shell_vol_up'], ['adb', 'shell', 'input', 'keyevent', 'KEYCODE_VOLUME_UP']),
            (self.strings['shell_vol_down'], ['adb', 'shell', 'input', 'keyevent', 'KEYCODE_VOLUME_DOWN']),
            (self.strings['shell_home'], ['adb', 'shell', 'input', 'keyevent', 'KEYCODE_HOME']),
            (self.strings['shell_back'], ['adb', 'shell', 'input', 'keyevent', 'KEYCODE_BACK']),
            (self.strings['shell_menu'], ['adb', 'shell', 'input', 'keyevent', 'KEYCODE_MENU']),
            (self.strings['shell_screencap'], ['adb', 'shell', 'screencap', '/sdcard/screenshot.png']),
            (self.strings['shell_screenrecord'], ['adb', 'shell', 'screenrecord', '/sdcard/demo.mp4', '--time-limit', '30']),
            (self.strings['shell_restart_systemui'], ['adb', 'shell', 'pkill', '-f', 'com.android.systemui']),
            (self.strings['shell_dns'], ['adb', 'shell', 'cmd', 'netd', 'resolver', 'flushnet']),
        ]
        for i, (text, cmd) in enumerate(shell_cmds):
            col = i % 3
            row = i // 3
            self.make_button(f, text, lambda c=cmd: self.run_task(c), width=28).grid(row=row, column=col, padx=10, pady=5)

    def create_tab_package_manager(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text=self.strings['tab_pm'])
        sf = ScrollableFrame(tab)
        sf.pack(fill="both", expand=True)
        f = sf.scrollable_frame

        tk.Label(f, text=self.strings['pm_header'], font=("Arial", 10, "bold"),
                 bg='#1e1e1e', fg='white').grid(row=0, column=0, columnspan=3, sticky="w", padx=10, pady=10)

        pm_cmds = [
            (self.strings['pm_list_all'], lambda: self.run_task(['adb', 'shell', 'pm', 'list', 'packages'])),
            (self.strings['pm_list_system'], lambda: self.run_task(['adb', 'shell', 'pm', 'list', 'packages', '-s'])),
            (self.strings['pm_list_third'], lambda: self.run_task(['adb', 'shell', 'pm', 'list', 'packages', '-3'])),
            (self.strings['pm_list_enabled'], lambda: self.run_task(['adb', 'shell', 'pm', 'list', 'packages', '-e'])),
            (self.strings['pm_list_disabled'], lambda: self.run_task(['adb', 'shell', 'pm', 'list', 'packages', '-d'])),
            (self.strings['pm_list_perms'], lambda: self.run_task(['adb', 'shell', 'pm', 'list', 'permissions'])),
            (self.strings['pm_clear'], lambda: self.run_pm_dialog('clear', self.strings['pkg_clear_prompt'])),
            (self.strings['pm_enable'], lambda: self.run_pm_dialog('enable', self.strings['pkg_enable_prompt'])),
            (self.strings['pm_disable'], lambda: self.run_pm_dialog('disable', self.strings['pkg_disable_prompt'])),
            (self.strings['pm_grant'], lambda: self.run_pm_dialog('grant', self.strings['pkg_grant_prompt'])),
            (self.strings['pm_revoke'], lambda: self.run_pm_dialog('revoke', self.strings['pkg_revoke_prompt'])),
            (self.strings['pm_path'], lambda: self.run_pm_dialog('path', self.strings['pkg_path_prompt'])),
            (self.strings['pm_info'], lambda: self.run_pm_dialog('info', self.strings['pkg_info_prompt'])),
            (self.strings['pm_install'], lambda: self.run_task(['adb', 'install', self.apk_file_path.get()]) if self.apk_file_path.get() else messagebox.showwarning("Error", self.strings['error_select_apk'])),
            (self.strings['pm_uninstall'], self.uninstall_package),
        ]
        row = 1
        for i, (text, cmd) in enumerate(pm_cmds):
            col = i % 3
            self.make_button(f, text, cmd, width=30).grid(row=row, column=col, padx=5, pady=5, sticky="w")
            if col == 2:
                row += 1

    def run_pm_dialog(self, action, prompt):
        if action in ('grant', 'revoke'):
            pair = simpledialog.askstring(self.strings[action + '_perm'], prompt)
            if pair:
                parts = pair.split(maxsplit=1)
                if len(parts) == 2:
                    self.run_task(['adb', 'shell', 'pm', action, parts[0], parts[1]])
        else:
            pkg = simpledialog.askstring(self.strings.get(action + '_pkg', self.strings['clear_data']), prompt)
            if pkg:
                if action == 'info':
                    self.run_task(['adb', 'shell', 'dumpsys', 'package', pkg])
                else:
                    self.run_task(['adb', 'shell', 'pm', action, pkg])

    def create_tab_screen_media(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text=self.strings['tab_screen'])
        sf = ScrollableFrame(tab)
        sf.pack(fill="both", expand=True)
        f = sf.scrollable_frame

        tk.Label(f, text=self.strings['screen_header'], font=("Arial", 10, "bold"),
                 bg='#1e1e1e', fg='white').grid(row=0, column=0, columnspan=2, sticky="w", padx=10, pady=10)

        screen_cmds = [
            (self.strings['screenshot_save'], ['adb', 'shell', 'screencap', '/sdcard/screenshot.png']),
            (self.strings['screenshot_pull'], ['adb', 'pull', '/sdcard/screenshot.png', '.']),
            (self.strings['record_start'], ['adb', 'shell', 'screenrecord', '/sdcard/demo.mp4', '--time-limit', '30']),
            (self.strings['record_pull'], ['adb', 'pull', '/sdcard/demo.mp4', '.']),
            (self.strings['set_res_1080'], ['adb', 'shell', 'wm', 'size', '1080x1920']),
            (self.strings['reset_res'], ['adb', 'shell', 'wm', 'size', 'reset']),
            (self.strings['set_density_320'], ['adb', 'shell', 'wm', 'density', '320']),
            (self.strings['reset_density'], ['adb', 'shell', 'wm', 'density', 'reset']),
            (self.strings['rotate_landscape'], ['adb', 'shell', 'content', 'insert', '--uri', 'content://settings/system', '--bind', 'name:s:user_rotation', '--bind', 'value:i:1']),
            (self.strings['rotate_portrait'], ['adb', 'shell', 'content', 'insert', '--uri', 'content://settings/system', '--bind', 'name:s:user_rotation', '--bind', 'value:i:0']),
            (self.strings['brightness_max'], ['adb', 'shell', 'settings', 'put', 'system', 'screen_brightness', '255']),
            (self.strings['brightness_min'], ['adb', 'shell', 'settings', 'put', 'system', 'screen_brightness', '30']),
            (self.strings['auto_bright_on'], ['adb', 'shell', 'settings', 'put', 'system', 'screen_brightness_mode', '1']),
            (self.strings['auto_bright_off'], ['adb', 'shell', 'settings', 'put', 'system', 'screen_brightness_mode', '0']),
        ]
        for i, (text, cmd) in enumerate(screen_cmds):
            col = i % 2
            row = 1 + i // 2
            self.make_button(f, text, lambda c=cmd: self.run_task(c), width=42).grid(row=row, column=col, padx=5, pady=5, sticky="w")

    def create_tab_network(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text=self.strings['tab_network'])
        sf = ScrollableFrame(tab)
        sf.pack(fill="both", expand=True)
        f = sf.scrollable_frame

        tk.Label(f, text=self.strings['network_header'], font=("Arial", 10, "bold"),
                 bg='#1e1e1e', fg='white').grid(row=0, column=0, columnspan=3, sticky="w", padx=10, pady=10)
        self.make_button(f, self.strings['adb_tcpip'],
                         lambda: self.run_task(['adb', 'tcpip', '5555']), width=42).grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.make_button(f, self.strings['adb_connect_ip'],
                         self.connect_adb_ip, width=42).grid(row=1, column=1, padx=5, pady=5, sticky="w")
        self.make_button(f, self.strings['adb_disconnect'],
                         self.disconnect_adb, width=42).grid(row=1, column=2, padx=5, pady=5, sticky="w")
        self.make_button(f, self.strings['show_ip'],
                         lambda: self.run_task(['adb', 'shell', 'ip', '-f', 'inet', 'addr', 'show', 'wlan0']),
                         width=42).grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.make_button(f, self.strings['ping_device'],
                         lambda: self.run_task(['adb', 'shell', 'ping', '-c', '4', '8.8.8.8']),  # исправлено
                         width=42).grid(row=2, column=1, padx=5, pady=5, sticky="w")

        tk.Label(f, text=self.strings['wifi_header'], font=("Arial", 10, "bold"),
                 bg='#1e1e1e', fg='white').grid(row=3, column=0, columnspan=3, sticky="w", padx=10, pady=10)
        self.make_button(f, self.strings['wifi_on'],
                         lambda: self.run_task(['adb', 'shell', 'svc', 'wifi', 'enable']), width=42).grid(row=4, column=0, padx=5, pady=5, sticky="w")
        self.make_button(f, self.strings['wifi_off'],
                         lambda: self.run_task(['adb', 'shell', 'svc', 'wifi', 'disable']), width=42).grid(row=4, column=1, padx=5, pady=5, sticky="w")
        self.make_button(f, self.strings['bluetooth_on'],
                         lambda: self.run_task(['adb', 'shell', 'svc', 'bluetooth', 'enable']), width=42).grid(row=5, column=0, padx=5, pady=5, sticky="w")
        self.make_button(f, self.strings['bluetooth_off'],
                         lambda: self.run_task(['adb', 'shell', 'svc', 'bluetooth', 'disable']), width=42).grid(row=5, column=1, padx=5, pady=5, sticky="w")

    def connect_adb_ip(self):
        ip = simpledialog.askstring(
            self.strings['dialog_connect_ip_title'],
            self.strings['dialog_connect_ip_prompt']
        )
        if ip and re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', ip):
            self.run_task(['adb', 'connect', f'{ip}:5555'])
        else:
            messagebox.showwarning("Ошибка", "Некорректный IP-адрес")

    def disconnect_adb(self):
        ip = simpledialog.askstring(
            self.strings['dialog_disconnect_title'],
            self.strings['dialog_disconnect_prompt']
        )
        if ip:
            self.run_task(['adb', 'disconnect', f'{ip}:5555'])
        else:
            self.run_task(['adb', 'disconnect'])

    def create_tab_settings(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text=self.strings['tab_settings'])
        sf = ScrollableFrame(tab)
        sf.pack(fill="both", expand=True)
        f = sf.scrollable_frame

        tk.Label(f, text=self.strings['settings_header'], font=("Arial", 10, "bold"),
                 bg='#1e1e1e', fg='white').grid(row=0, column=0, columnspan=2, sticky="w", padx=10, pady=10)
        settings_cmds = [
            (self.strings['settings_list_global'], ['adb', 'shell', 'settings', 'list', 'global']),
            (self.strings['settings_list_secure'], ['adb', 'shell', 'settings', 'list', 'secure']),
            (self.strings['settings_list_system'], ['adb', 'shell', 'settings', 'list', 'system']),
            (self.strings['settings_timeout_30'], ['adb', 'shell', 'settings', 'put', 'system', 'screen_off_timeout', '30000']),
            (self.strings['settings_timeout_5min'], ['adb', 'shell', 'settings', 'put', 'system', 'screen_off_timeout', '300000']),
            (self.strings['settings_anim_05'], ['adb', 'shell', 'settings', 'put', 'global', 'window_animation_scale', '0.5']),
            (self.strings['settings_anim_0'], ['adb', 'shell', 'settings', 'put', 'global', 'window_animation_scale', '0']),
            (self.strings['settings_usb_on'], ['adb', 'shell', 'settings', 'put', 'global', 'usb_mass_storage_enabled', '1']),
            (self.strings['settings_usb_off'], ['adb', 'shell', 'settings', 'put', 'global', 'usb_mass_storage_enabled', '0']),
            (self.strings['settings_android_ver'], ['adb', 'shell', 'getprop', 'ro.build.version.release']),
            (self.strings['settings_build'], ['adb', 'shell', 'getprop', 'ro.build.display.id']),
            (self.strings['settings_devicename'], ['adb', 'shell', 'settings', 'put', 'global', 'device_name', 'NewDevice']),
        ]
        for i, (text, cmd) in enumerate(settings_cmds):
            col = i % 2
            row = 1 + i // 2
            self.make_button(f, text, lambda c=cmd: self.run_task(c), width=42).grid(row=row, column=col, padx=5, pady=5, sticky="w")

        tk.Label(f, text=self.strings['buildprop_header'], font=("Arial", 10, "bold"),
                 bg='#1e1e1e', fg='white').grid(row=10, column=0, columnspan=2, sticky="w", padx=10, pady=10)
        self.make_button(f, self.strings['buildprop_model'],
                         self.edit_buildprop_model, width=42).grid(row=11, column=0, padx=5, pady=5, sticky="w")
        self.make_button(f, self.strings['buildprop_incremental'],
                         self.edit_buildprop_incremental, width=42).grid(row=11, column=1, padx=5, pady=5, sticky="w")

    def edit_buildprop_model(self):
        val = simpledialog.askstring(
            self.strings['dialog_edit_model_title'],
            self.strings['dialog_edit_model_prompt']
        )
        if val and re.match(r'^[a-zA-Z0-9_\-\. ]+$', val):
            self.run_task(['adb', 'shell', 'su', '-c', f'setprop ro.product.model {shlex.quote(val)}'], shell=True)
        else:
            messagebox.showwarning("Ошибка", "Недопустимое значение")

    def edit_buildprop_incremental(self):
        val = simpledialog.askstring(
            self.strings['dialog_edit_inc_title'],
            self.strings['dialog_edit_inc_prompt']
        )
        if val and re.match(r'^[a-zA-Z0-9_\-\. ]+$', val):
            self.run_task(['adb', 'shell', 'su', '-c', f'setprop ro.build.version.incremental {shlex.quote(val)}'], shell=True)
        else:
            messagebox.showwarning("Ошибка", "Недопустимое значение")

    def create_tab_log_debug(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text=self.strings['tab_log'])
        sf = ScrollableFrame(tab)
        sf.pack(fill="both", expand=True)
        f = sf.scrollable_frame

        tk.Label(f, text=self.strings['log_header'], font=("Arial", 10, "bold"),
                 bg='#1e1e1e', fg='white').grid(row=0, column=0, columnspan=2, sticky="w", padx=10, pady=10)

        log_buttons = [
            (self.strings['logcat_all'], ['adb', 'logcat', '-d']),
            (self.strings['logcat_errors'], ['adb', 'logcat', '-d', '*:E']),
            (self.strings['logcat_clear'], ['adb', 'logcat', '-c']),
            (self.strings['logcat_filter'], self.logcat_filter_dialog),
            (self.strings['dumpsys_all'], ['adb', 'shell', 'dumpsys']),
            (self.strings['dumpsys_activity'], ['adb', 'shell', 'dumpsys', 'activity']),
            (self.strings['dumpsys_mem'], ['adb', 'shell', 'dumpsys', 'meminfo']),
            (self.strings['dumpsys_bat'], ['adb', 'shell', 'dumpsys', 'battery']),
            (self.strings['dumpsys_wifi'], ['adb', 'shell', 'dumpsys', 'wifi']),
            (self.strings['dumpsys_bt'], ['adb', 'shell', 'dumpsys', 'bluetooth_manager']),
            (self.strings['dumpsys_pkg'], ['adb', 'shell', 'dumpsys', 'package']),
            (self.strings['bugreport'], ['adb', 'shell', 'bugreport', '/sdcard/bugreport.txt']),
            (self.strings['bugreport_pull'], ['adb', 'pull', '/sdcard/bugreport.txt', '.']),
            (self.strings['net_stats'], ['adb', 'shell', 'cat', '/proc/net/dev']),
        ]
        row = 1
        for i, (text, cmd) in enumerate(log_buttons):
            col = i % 2
            if callable(cmd):
                btn = self.make_button(f, text, cmd, width=42)
            else:
                btn = self.make_button(f, text, lambda c=cmd: self.run_task(c), width=42)
            btn.grid(row=row, column=col, padx=5, pady=5, sticky="w")
            if col == 1:
                row += 1

    def logcat_filter_dialog(self):
        tag = simpledialog.askstring(
            self.strings['dialog_logcat_filter_title'],
            self.strings['dialog_logcat_filter_prompt']
        )
        if not tag:
            return
        # Выполняем adb logcat -d и фильтруем в Python
        def filter_logcat():
            try:
                proc = subprocess.Popen(['adb', 'logcat', '-d'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                output, _ = proc.communicate()
                lines = output.splitlines()
                filtered = [line for line in lines if tag in line]
                if filtered:
                    self.log("\n".join(filtered))
                else:
                    self.log(f"[Нет строк с тегом '{tag}']")
            except Exception as e:
                self.log(f"[Ошибка] {str(e)}")
        # Запускаем в отдельном потоке, чтобы не блокировать GUI
        threading.Thread(target=filter_logcat, daemon=True).start()

    def create_tab_fastboot_extra(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text=self.strings['tab_fb_extra'])
        sf = ScrollableFrame(tab)
        sf.pack(fill="both", expand=True)
        f = sf.scrollable_frame

        tk.Label(f, text=self.strings['fb_extra_header'], font=("Arial", 10, "bold"),
                 bg='#1e1e1e', fg='white').grid(row=0, column=0, columnspan=2, sticky="w", padx=10, pady=10)

        fb_buttons = [
            (self.strings['fb_unlock'], ['fastboot', 'oem', 'unlock']),
            (self.strings['fb_lock'], ['fastboot', 'oem', 'lock']),
            (self.strings['fb_unlock_info'], ['fastboot', 'oem', 'unlock-info']),
            (self.strings['fb_current_slot'], ['fastboot', 'getvar', 'current-slot']),
            (self.strings['fb_getvar_all'], ['fastboot', 'getvar', 'all']),
            (self.strings['fb_set_slot_a'], ['fastboot', '--set-active=a']),
            (self.strings['fb_set_slot_b'], ['fastboot', '--set-active=b']),
            (self.strings['fb_edl'], ['fastboot', 'oem', 'edl']),
            (self.strings['fb_fastbootd'], ['fastboot', 'reboot', 'fastboot']),
            (self.strings['fb_erase'], self.fastboot_erase_partition),
            (self.strings['fb_format'], self.fastboot_format_partition),
            (self.strings['fb_flash'], self.flash_selected_image),
            (self.strings['fb_boot'], self.boot_selected_image),
        ]
        row = 1
        for i, (text, cmd) in enumerate(fb_buttons):
            col = i % 2
            if callable(cmd):
                btn = self.make_button(f, text, cmd, width=42)
            else:
                btn = self.make_button(f, text, lambda c=cmd: self.run_task(c), width=42)
            btn.grid(row=row, column=col, padx=5, pady=5, sticky="w")
            if col == 1:
                row += 1

    def fastboot_erase_partition(self):
        part = simpledialog.askstring(
            self.strings['dialog_erase_part_title'],
            self.strings['dialog_erase_part_prompt']
        )
        if part and messagebox.askyesno("Confirm", self.strings['confirm_erase'].format(part=part)):
            self.run_task(['fastboot', 'erase', part])

    def fastboot_format_partition(self):
        part = simpledialog.askstring(
            self.strings['dialog_format_part_title'],
            self.strings['dialog_format_part_prompt']
        )
        if part and messagebox.askyesno("Confirm", self.strings['confirm_format'].format(part=part)):
            self.run_task(['fastboot', 'format', part])

    def create_tab_custom_command(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text=self.strings['tab_custom'])
        sf = ScrollableFrame(tab)
        sf.pack(fill="both", expand=True)
        f = sf.scrollable_frame

        tk.Label(f, text=self.strings['custom_header'], font=("Arial", 10, "bold"),
                 bg='#1e1e1e', fg='white').pack(anchor="w", padx=10, pady=10)
        tk.Entry(f, textvariable=self.custom_command, width=80,
                 bg='#3c3c3c', fg='white', insertbackground='white').pack(padx=10, pady=5, anchor="w")
        self.make_button(f, self.strings['custom_execute'], self.run_custom_command,
                         bg='#0078d7', fg='white').pack(padx=10, pady=5, anchor="w")

    def run_custom_command(self):
        cmd = self.custom_command.get().strip()
        if cmd:
            self.run_task(cmd, shell=True)
        else:
            messagebox.showwarning("Error", self.strings['error_enter_cmd'])


if __name__ == "__main__":
    root = tk.Tk()
    app = PhoneToolsTweakerApp(root)
    root.mainloop()
