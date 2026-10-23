"""生成地点目录与详情页，并在多语种渲染时填入地点资料。"""

from __future__ import annotations

import html
import json
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).parent
DATA = ROOT / "static/locations-data.json"
LOCALES = ROOT / "static/i18n/locations"
RECYCLER_SLUGS = {"gas-station", "parking", "town", "warehouse", "lumberjack", "miner"}
RECYCLER_TEXT = {
    "zh": ("回收机", "此处有回收机。把可回收物拆成制作资源；运转声可能引来其他玩家。", "需要回收物资时，可去加油站、停车场、城镇、仓库、伐木工人或矿工。"),
    "en": ("Recycler", "There is a recycler here. It breaks down recyclable items and makes noise while running.", "For recycling, visit a gas station, parking lot, town, warehouse, Lumberjack or Miner."),
    "ja": ("リサイクル機", "ここにはリサイクル機があります。使うと音が出るため、周囲のプレイヤーに注意してください。", "リサイクルするなら、ガソリンスタンド、駐車場、町、倉庫、木こり、鉱夫へ向かってください。"),
    "ko": ("재활용 기계", "이곳에 재활용 기계가 있습니다. 작동 소리를 다른 플레이어가 들을 수 있으니 주의하세요.", "재활용이 필요하면 주유소, 주차장, 마을, 창고, 벌목꾼 또는 광부에게 가세요."),
    "fr": ("Recycleur", "Un recycleur se trouve ici. Son fonctionnement fait du bruit et peut attirer d'autres joueurs.", "Pour recycler, rendez-vous à la station-service, au parking, en ville, à l'entrepôt, chez le bûcheron ou chez le mineur."),
    "de": ("Recycler", "Hier steht ein Recycler. Er macht beim Betrieb Geräusche, die andere Spieler hören können.", "Zum Recyceln kannst du zur Tankstelle, zum Parkplatz, in die Stadt, zum Lagerhaus, zum Holzfäller oder zum Bergarbeiter gehen."),
    "es": ("Recicladora", "Aquí hay una recicladora. Hace ruido al funcionar y puede atraer a otros jugadores.", "Para reciclar, ve a la gasolinera, el aparcamiento, la ciudad, el almacén, el leñador o el minero."),
    "pt": ("Recicladora", "Há uma recicladora aqui. Ela faz barulho ao funcionar e pode atrair outros jogadores.", "Para reciclar, vá ao posto de gasolina, estacionamento, cidade, armazém, lenhador ou mineiro."),
    "ru": ("Переработчик", "Здесь есть переработчик. Во время работы он шумит и может привлечь других игроков.", "Для переработки отправляйтесь на заправку, парковку, в город, на склад, к леснику или шахтёру."),
}
IMAGE_CAPTION = {
    "zh": "游戏官方配图", "en": "Official game image", "ja": "ゲーム公式画像", "ko": "게임 공식 이미지",
    "fr": "Image officielle du jeu", "de": "Offizielles Spielbild", "es": "Imagen oficial del juego",
    "pt": "Imagem oficial do jogo", "ru": "Официальное изображение игры",
}
NAMES = {
    "ja": ["ガソリンスタンド", "駐車場", "町", "倉庫", "廃工場とルーレット", "木こり", "鉱夫", "工場", "隕石ドリル", "軍事基地", "墜落機", "灯台", "原子力発電所", "鉄道駅", "送電塔"],
    "ko": ["주유소", "주차장", "마을", "창고", "폐공장과 행운의 바퀴", "벌목꾼", "광부", "공장", "운석 드릴", "군사 기지", "추락 비행기", "등대", "원자력 발전소", "기차역", "송전탑"],
    "fr": ["Station-service", "Parking", "Ville", "Entrepôt", "Usine abandonnée et roue de la chance", "Bûcheron", "Mineur", "Usine", "Foreuse de météorite", "Base militaire", "Avion écrasé", "Phare", "Centrale nucléaire", "Gare ferroviaire", "Pylône électrique"],
    "de": ["Tankstelle", "Parkplatz", "Stadt", "Lagerhaus", "Verlassene Fabrik und Glücksrad", "Holzfäller", "Bergarbeiter", "Fabrik", "Meteoritenbohrer", "Militärbasis", "Flugzeugwrack", "Leuchtturm", "Kernkraftwerk", "Bahnhof", "Strommast"],
    "es": ["Gasolinera", "Aparcamiento", "Ciudad", "Almacén", "Fábrica abandonada y ruleta", "Leñador", "Minero", "Fábrica", "Taladro del meteorito", "Base militar", "Avión siniestrado", "Faro", "Central nuclear", "Estación de tren", "Torre eléctrica"],
    "pt": ["Posto de gasolina", "Estacionamento", "Cidade", "Armazém", "Fábrica abandonada e roleta", "Lenhador", "Mineiro", "Fábrica", "Broca do meteorito", "Base militar", "Avião acidentado", "Farol", "Usina nuclear", "Estação ferroviária", "Torre elétrica"],
    "ru": ["Заправка", "Парковка", "Город", "Склад", "Заброшенный завод и колесо удачи", "Лесник", "Шахтёр", "Завод", "Бур на метеорите", "Военная база", "Разбившийся самолёт", "Маяк", "АЭС", "Железнодорожная станция", "Опора ЛЭП"],
}

LABELS = {
    "zh": ["地点", "按特殊玩法、主要收益和风险查找地点。地图位置随服务器变化。", "特殊玩法", "主要收益", "风险", "资料来源", "返回地点目录", "查看详情", "资料核对于 2026 年 10 月", "地点介绍"],
    "en": ["Places", "Find places by activity, rewards and risk. Map positions vary by server.", "What to do", "Main rewards", "Risks", "Sources", "All places", "Details", "Reviewed October 2026", "Place guide"],
    "ja": ["場所", "遊び方、主な報酬、危険から場所を探せます。位置はサーバーによって変わります。", "遊び方", "主な報酬", "危険", "出典", "場所一覧へ", "詳細", "2026年10月確認", "場所ガイド"],
    "ko": ["장소", "특별한 활동, 주요 보상과 위험으로 장소를 찾아보세요. 위치는 서버마다 달라집니다.", "특별한 활동", "주요 보상", "위험", "출처", "장소 목록", "자세히", "2026년 10월 확인", "장소 안내"],
    "fr": ["Lieux", "Trouvez un lieu selon ses activités, ses gains et ses risques. La carte varie selon le serveur.", "Activités", "Principaux gains", "Risques", "Sources", "Tous les lieux", "Détails", "Vérifié en octobre 2026", "Guide des lieux"],
    "de": ["Orte", "Finde Orte nach Aktivitäten, Ertrag und Risiko. Die Karte variiert je nach Server.", "Aktivitäten", "Ertrag", "Risiken", "Quellen", "Alle Orte", "Details", "Stand: Oktober 2026", "Ortsführer"],
    "es": ["Lugares", "Busca lugares por actividad, recompensas y riesgos. El mapa varía según el servidor.", "Actividades", "Recompensas", "Riesgos", "Fuentes", "Todos los lugares", "Detalles", "Revisado en octubre de 2026", "Guía de lugares"],
    "pt": ["Locais", "Encontre locais por atividades, recompensas e riscos. O mapa varia conforme o servidor.", "Atividades", "Recompensas", "Riscos", "Fontes", "Todos os locais", "Detalhes", "Conferido em outubro de 2026", "Guia de locais"],
    "ru": ["Локации", "Ищите места по занятиям, наградам и рискам. Положение на карте зависит от сервера.", "Что делать", "Награды", "Риски", "Источники", "Все локации", "Подробнее", "Проверено в октябре 2026", "Гид по локациям"],
}


def rows() -> list[dict]:
    data = json.loads(DATA.read_text(encoding="utf-8"))
    assert len({row["slug"] for row in data}) == len(data)
    assert all(len(row["zh"]) == len(row["en"]) == 5 and row["sources"] for row in data)
    return data


def write_source_pages(header, footer) -> int:
    """源页面只放结构；正文从显式资料文件写入各语种页面。"""
    directory = ROOT / "locations"
    directory.mkdir(exist_ok=True)
    for old in directory.glob("*.html"):
        old.unlink()
    for slug in ["index", *(row["slug"] for row in rows())]:
        source = f'''<!doctype html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><link rel="stylesheet" href="../styles.css"><link rel="stylesheet" href="../static/locations.css"></head><body>{header("../", selected="locations")}<main class="locations-shell" data-location-page="{html.escape(slug)}"></main>{footer()}</body></html>'''
        (directory / f"{slug}.html").write_text(source, encoding="utf-8")
    return len(rows())


def render_locations(soup: BeautifulSoup, page: str, lang: str, locale_root: str) -> None:
    """填充详情，站内链接始终指向当前语种。"""
    data = rows()
    mapping = json.loads((LOCALES / f"{lang}.json").read_text(encoding="utf-8"))
    labels = LABELS[lang]
    target = soup.select_one(".locations-shell")
    slug = target["data-location-page"]
    title_by_slug = {}
    for index, row in enumerate(data):
        title_by_slug[row["slug"]] = NAMES[lang][index] if lang in NAMES else mapping[row["slug"]][0]

    def add(markup: str) -> None:
        target.append(BeautifulSoup(markup, "html.parser"))

    if slug == "index":
        cards = "".join(
            f'<a class="locations-card" href="{html.escape(locale_root + "locations/" + row["slug"] + ".html")}">'
            + (f'<img class="locations-card-image" src="{html.escape(locale_root + "../" + row["image"])}" alt="" loading="lazy">' if row.get("image") else "")
            + f'<strong>{html.escape(title_by_slug[row["slug"]])}</strong>'
            f'<span>{html.escape(mapping[row["slug"]][1])}</span><small>{html.escape(labels[7])} →</small></a>'
            for row in data
        )
        add(f'<div class="locations-intro"><span class="locations-eyebrow">OXIDE WORLD</span><h1>{html.escape(labels[0])}</h1><p>{html.escape(labels[1])}</p></div><div class="locations-grid">{cards}</div>')
    else:
        row = next(row for row in data if row["slug"] == slug)
        content = mapping[slug]
        back = html.escape(locale_root + "locations/")
        body = "".join(
            f'<section class="locations-section"><h2>{html.escape(label)}</h2><p>{html.escape(value)}</p></section>'
            for label, value in zip(labels[2:5], content[2:5])
        )
        recycler = RECYCLER_TEXT[lang]
        recycler_text = recycler[1] if slug in RECYCLER_SLUGS else recycler[2]
        body += f'<section class="locations-section"><h2>{html.escape(recycler[0])}</h2><p>{html.escape(recycler_text)}</p></section>'
        photo = ""
        if row.get("image"):
            caption = IMAGE_CAPTION[lang]
            photo = (f'<figure class="locations-photo"><img src="{html.escape(locale_root + "../" + row["image"])}" '
                     f'alt="{html.escape(title_by_slug[slug])}" loading="lazy"><figcaption>{html.escape(caption)}</figcaption></figure>')
        add(f'<article class="locations-detail"><a class="locations-back" href="{back}">← {html.escape(labels[6])}</a><span class="locations-eyebrow">{html.escape(labels[9])}</span><h1>{html.escape(title_by_slug[slug])}</h1><p class="locations-lead">{html.escape(content[1])}</p>{photo}<div class="locations-sections">{body}</div></article>')
