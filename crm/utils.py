from logly import logger

cust_color = {"INFO": "GREEN", "ERROR": "BRIGHT_RED"}


def configure_logging():
    logger.configure(
        level="INFO",
        json=False,
        color=True,
        # console=True,                 # Вывод в log-файлы
        # console_levels=cons_levels,   # Вывод в log-файлы
        level_colors=cust_color,
        # color_callback=custom_color,
        auto_sink=True,
        # auto_sink_levels=a_sink_levels,
    )
    logger.info("Настроили logger!")
