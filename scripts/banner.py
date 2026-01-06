#!/usr/bin/env python3
"""
QuantResearch 启动横幅

显示项目启动的 ASCII Art 和服务信息。
作者: MorpheusZ
"""

import sys
import shutil

# ============================================
# ANSI 颜色
# ============================================
ORANGE = "\033[38;5;208m"
CYAN = "\033[96m"
GREEN = "\033[92m"
WHITE = "\033[97m"
DIM = "\033[2m"
BOLD = "\033[1m"
RESET = "\033[0m"

CLEAR_SCREEN = "\033[2J"

def move_to(row: int, col: int) -> str:
    return f"\033[{row};{col}H"


# ============================================
# Bitcoin 图案
# ============================================
COIN_ART = """
@@@@@@@@@@@@@@@@@%*-:.:-----:.:-*@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@*-:=##**+%+**%#%%#*@*-:-*@@@@@@@@@@@@@
@@@@@@@@@@+.=*%*#%%-..#*:  =#*.-#%#*@*=.+@@@@@@@@@@
@@@@@@@@--#*#%=.:*#+***********+#*+:+##**--%@@@@@@@
@@@@@@::%#**#%*****###+:.@**####****-##@#*%::@@@@@@
@@@@#:*##* :+***###*-::+=:.:*#**#*****+. +#@*:#@@@@
@@@=:####**+=-=:+=**:  *+  .*#*#**#***=+*#%@##:=@@@
@@=-##= -**#**+===-=.  =-   :+**##*##+=***: ##*-=@@
@*-##%#**###**-                  .###-+****+*%*#-*@
@-#@#.=***++***+*#.    #@@@%=     :#*-#####*-:#%+-%
#-@@%-*###******#-.    %@@@@@=    :####%%##@+:#%%-#
=-###**+*##%%%%##=.    %@@@@#    .%=%%##%*#=====*-=
-=#* -++##%%###+::.               -=%%#%#***+::+*-=
=-+%%*++#%##%%%#==:    %@@@@@%:     @++#=-=**==#*:=
#.*#+:*##%##***+:-.    %@@@@@@@:    ##**%*--+***+.#
@-+++.=*+*****=***.    %@@@@@@+     =**#********=:%
@*:#+##***###*+=                   -***##%@@@@#%:*@
@@=-@%- =*###++-. .     .     .:=**##**#@*- *#*:=@@
@@@=:#**#*#**=**##**=  :*   =-:+==****+#*#=*#*:+@@@
@@@@#:*##- -***###**+. =#. .**###***=++-.%%**:#@@@@
@@@@@@-:##=#*#*****###==:@##*#*##****%+*#*#:-@@@@@@
@@@@@@@@--#*#+:.+#****************..=%##*--@@@@@@@@
@@@@@@@@@@+ =*@*#%-  +#+..=%*  :%%#*@#= *@@@@@@@@@@
@@@@@@@@@@@@@*-:-+%%#**#*#**%+%**+=:-*@@@@@@@@@@@@@
@@@@@@@@@@@@@@@@@@*=:..::-::..:=*@@@@@@@@@@@@@@@@@@
"""


# ============================================
# Logo 和服务信息
# ============================================

LOGO = f"""
{CYAN}   ██████╗  {ORANGE}██╗   ██╗ █████╗ ███╗   ██╗████████╗{CYAN}   ██████╗ ███████╗███████╗███████╗ █████╗ ██████╗  ██████╗██╗  ██╗
{CYAN}  ██╔═══██╗ {ORANGE}██║   ██║██╔══██╗████╗  ██║╚══██╔══╝{CYAN}   ██╔══██╗██╔════╝██╔════╝██╔════╝██╔══██╗██╔══██╗██╔════╝██║  ██║
{CYAN}  ██║   ██║ {ORANGE}██║   ██║███████║██╔██╗ ██║   ██║   {CYAN}   ██████╔╝█████╗  ███████╗█████╗  ███████║██████╔╝██║     ███████║
{CYAN}  ██║▄▄ ██║ {ORANGE}██║   ██║██╔══██║██║╚██╗██║   ██║   {CYAN}   ██╔══██╗██╔══╝  ╚════██║██╔══╝  ██╔══██║██╔══██╗██║     ██╔══██║
{CYAN}  ╚██████╔╝ {ORANGE}╚██████╔╝██║  ██║██║ ╚████║   ██║   {CYAN}   ██║  ██║███████╗███████║███████╗██║  ██║██║  ██║╚██████╗██║  ██║
{CYAN}   ╚══▀▀═╝  {ORANGE} ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝   {CYAN}   ╚═╝  ╚═╝╚══════╝╚══════╝╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝{RESET}

{DIM}                                              AI Platform  |  Author: MorpheusZ{RESET}
"""

YELLOW = "\033[93m"

def get_services() -> str:
    """生成服务地址文本"""
    return f"""
{DIM}════════════════════════════════════════════════════════════════════════════════════════════════════════════════════{RESET}

{WHITE}{BOLD}                                                        服务地址{RESET}

        {GREEN}Frontend        {RESET}http://localhost:5173                              {DIM}React Dashboard{RESET}
        {GREEN}API             {RESET}http://localhost:8000                              {DIM}FastAPI Backend{RESET}
        {GREEN}API Docs        {RESET}http://localhost:8000/docs                         {DIM}Swagger UI{RESET}

        {CYAN}Factor MCP      {RESET}http://localhost:6789/mcp                          {DIM}因子知识库{RESET}
        {CYAN}Data MCP        {RESET}http://localhost:6790/mcp                          {DIM}数据服务{RESET}
        {CYAN}Strategy MCP    {RESET}http://localhost:6791/mcp                          {DIM}策略知识库{RESET}
        {CYAN}Note MCP        {RESET}http://localhost:6792/mcp                          {DIM}经验笔记{RESET}

{DIM}════════════════════════════════════════════════════════════════════════════════════════════════════════════════════{RESET}
"""


def _center(text: str, term_width: int) -> str:
    """居中文本"""
    clean = text
    for c in [ORANGE, CYAN, GREEN, WHITE, DIM, BOLD, RESET, YELLOW]:
        clean = clean.replace(c, "")
    pad = (term_width - len(clean)) // 2
    return " " * max(0, pad) + text


def _add_padding(text: str, padding: int) -> str:
    """给文本添加固定左边距"""
    return " " * padding + text


def print_banner(duration: float = 0, clear_screen: bool = False):
    """打印启动横幅"""
    term_width, _ = shutil.get_terminal_size((120, 50))

    # 可选清屏
    if clear_screen:
        sys.stdout.write(CLEAR_SCREEN)
        sys.stdout.write(move_to(1, 1))
    else:
        # 打印分隔空行
        print("\n" * 2)

    # 打印图案占位区
    for line in COIN_ART.split('\n'):
        print(_center(line, term_width))

    # 打印 Logo
    for line in LOGO.split('\n'):
        print(_center(line, term_width))

    # 打印服务信息 - 使用固定左边距保持对齐
    # 计算基于分隔线宽度的居中偏移
    separator_width = 116  # 分隔线的字符宽度
    padding = max(0, (term_width - separator_width) // 2)
    services = get_services()
    for line in services.split('\n'):
        print(_add_padding(line, padding))

    sys.stdout.flush()

    # 如果指定了持续时间，等待后返回
    if duration > 0:
        import time
        time.sleep(duration)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="QuantResearch 启动横幅")
    parser.add_argument("-t", "--time", type=float, default=0, help="显示时间（秒），0=一直显示")
    parser.add_argument("-c", "--clear", action="store_true", help="清屏后显示")
    args = parser.parse_args()

    print_banner(duration=args.time, clear_screen=args.clear)


if __name__ == "__main__":
    main()
