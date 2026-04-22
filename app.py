# app.py - Полный рабочий вариант
import streamlit as st
import os
import json
from groq import Groq
from datetime import datetime
from pathlib import Path
from difflib import SequenceMatcher
import uuid

# === КОНФИГУРАЦИЯ ===
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
PROJECTS_FILE = DATA_DIR / "projects.json"
EXAMPLES_ROOT = Path("examples")
EXAMPLES_ROOT.mkdir(exist_ok=True)


# === УТИЛИТЫ: ПРОЕКТЫ ===
def load_projects():
    if not PROJECTS_FILE.exists():
        return []
    with open(PROJECTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_projects(projects):
    with open(PROJECTS_FILE, "w", encoding="utf-8") as f:
        json.dump(projects, f, ensure_ascii=False, indent=2)


def create_project(name: str, domain: str, niche: str, brand: str = "") -> dict:
    pid = name.lower().replace(" ", "_").replace("-", "_")[:20]
    project = {
        "id": pid,
        "name": name,
        "domain": domain,
        "brand": brand if brand else name,
        "niche": niche,
        "anchors": [],
        "noanchors": [],
        "created_at": datetime.now().isoformat(),
    }
    projects = load_projects()
    projects.append(project)
    save_projects(projects)
    (EXAMPLES_ROOT / pid).mkdir(exist_ok=True)
    return project


def update_project(updated: dict):
    projects = load_projects()
    for i, p in enumerate(projects):
        if p["id"] == updated["id"]:
            projects[i] = updated
            break
    save_projects(projects)


# === УТИЛИТЫ: ПРИМЕРЫ ===
def get_project_examples_dir(pid: str) -> Path:
    d = EXAMPLES_ROOT / pid
    d.mkdir(exist_ok=True)
    return d


def load_project_examples(pid: str):
    examples = []
    for f in get_project_examples_dir(pid).glob("*.json"):
        try:
            with open(f, "r", encoding="utf-8") as file:
                examples.append(json.load(file))
        except:
            continue
    return examples


def save_project_example(pid: str, topic, anchor, article_snippet, prompt_snippet):
    filename = f"example_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    data = {
        "topic": topic,
        "anchor": anchor,
        "article_snippet": article_snippet[:500],
        "prompt_snippet": prompt_snippet[:500],
        "timestamp": datetime.now().isoformat(),
    }
    with open(get_project_examples_dir(pid) / filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return filename


def find_similar_example(topic, anchor, examples, threshold=0.4):
    if not examples:
        return None
    query = f"{topic} {anchor}".lower()
    best_match, best_score = None, threshold
    for ex in examples:
        score = SequenceMatcher(
            None, query, f"{ex['topic']} {ex['anchor']}".lower()
        ).ratio()
        if score > best_score:
            best_match, best_score = ex, score
    return best_match


def generate_meta_tags(topic, anchor, niche, domain, brand, client):
    """Генерирует SEO Title и Description по вашим шаблонам"""

    # Примеры ваших успешных мета-тегов для few-shot обучения
    examples = """
ПРИМЕРЫ ОТЛИЧНЫХ МЕТА-ТЕГОВ:

1. Тема: Автоцистерны для питьевой воды
   Title: Автоцистерна для питьевой воды — требования по СанПиН
   Description: Чем цистерна для питьевой воды отличается от технической: материал, маркировка, документы. Как соблюсти СанПиН и ГОСТ при производстве и эксплуатации. {brand}.

2. Тема: Купить ППУА в Миассе
   Title: Купить ППУА в Миассе — в наличии или под заказ
   Description: Готовые паровые установки ППУА в наличии на складе в Миассе. Быстрая поставка от 1 дня, доставка по РФ. Заказ под вашу задачу — за 10 дней. {brand}.

3. Тема: Как выбрать ППУА для промывки скважин
   Title: Как выбрать ППУА для промывки скважин под месторождение
   Description: Подбор паровой установки по типу нефти, глубине скважины и климату. Готовые решения от {brand} для Урала, Сибири, Крайнего Севера. Доставка по РФ.

4. Тема: Гарантия на ППУА
   Title: Гарантия и сервис ППУА от завода-производителя
   Description: Что входит в гарантию на ППУА: сроки, условия, выездной сервис, запчасти, обучение персонала. Поддержка от {brand} — до последнего дня эксплуатации.

5. Тема: Дооснащение ППУА
   Title: Дооснащение ППУА: БРС, газовая горелка, автоматика
   Description: Как модифицировать ППУА под свои задачи: установка БРС, переход на газовую горелку, современная автоматика. Возможности завода {brand} — от базовой комплектации до спецрешений.

6. Тема: Обработка скважин кислотой
   Title: Обработка скважин кислотой: требования к оборудованию | {brand}
   Description: Требования к кислотным агрегатам для обработки скважин: цистерны из нержавейки, системы безопасности, нормативы ГОСТ и Ростехнадзора. Экспертный гайд от {brand}.

7. Тема: Оборудование для мастерской
   Title: Оборудование для передвижной мастерской: чек-лист 2026
   Description: Чек-лист оборудования для передвижной мастерской: генераторы, верстаки, инструмент. Подбор под задачи: сварка, ремонт труб, диагностика. Рекомендации экспертов {brand}.
""".format(brand=brand)

    prompt = f"""Ты профессиональный SEO-специалист для B2B (промышленность, спецтехника).

ЗАДАЧА: Создай мета-теги для статьи.

ВХОДНЫЕ ДАННЫЕ:
• Тема статьи: {topic}
• Ключевой запрос (анкор): {anchor}
• Ниша: {niche}
• Домен: {domain}
• Бренд: {brand}

{examples}

ТРЕБОВАНИЯ К TITLE:
✅ Формат: один из паттернов выше (с двоеточием, тире или вертикальной чертой)
✅ Длина: 50-65 символов (с пробелами)
✅ Ключ в начале или середине
✅ Коммерческий интент: купить, выбрать, заказать, требования, гарантия, модификация
✅ Можно добавить бренд через " | {brand}" в конце (если место позволяет)
✅ ЗАКАНЧИВАТЬ НА ПОЛНОМ СЛОВЕ (не обрывать)

ТРЕБОВАНИЯ К DESCRIPTION:
✅ Длина: 140-160 символов (с пробелами)
✅ Начинается с ответа / сравнения / перечисления
✅ Конкретика: цифры, сроки, локации, нормативы (ГОСТ, СанПиН, Ростехнадзор)
✅ Упоминание бренда в конце: "{brand}."
✅ Призыв к действию или выгода
✅ ЗАКАНЧИВАТЬ НА ПОЛНОМ СЛОВЕ (не обрывать)

ФОРМАТ ОТВЕТА СТРОГО:
Title: [ваш текст]
Description: [ваш текст]

Выведи только Title и Description, без пояснений."""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=250,
        )
        raw = response.choices[0].message.content.strip()

        title = ""
        description = ""

        if "Title:" in raw and "Description:" in raw:
            title = raw.split("Title:")[1].split("Description:")[0].strip()
            description = raw.split("Description:")[1].strip()
        elif "Title:" in raw:
            title = raw.split("Title:")[1].split("\n")[0].strip()
            for line in raw.split("\n"):
                if "description" in line.lower() and ":" in line:
                    description = line.split(":", 1)[1].strip()
                    break

        # === УМНАЯ ОБРЕЗКА (по границе слов + без висячих знаков) ===
        def smart_truncate(text, max_length):
            """Обрезает текст до max_length, но по границе слова и без висячих знаков"""
            if len(text) <= max_length:
                return text.strip()

            # Обрезаем
            truncated = text[:max_length].rstrip()

            # Убираем висячие знаки препинания
            while truncated and truncated[-1] in " ,;:.-!?":
                truncated = truncated[:-1]

            # Находим последний пробел (границу слова)
            last_space = truncated.rfind(" ")
            if last_space > max_length * 0.7:  # Если есть пробел в последних 30%
                return truncated[:last_space].strip()

            return truncated.strip()

        title = smart_truncate(title, 65)
        description = smart_truncate(description, 160)

        # Добавляем бренд в конец description, если его там нет
        if (
            brand.lower() not in description.lower()
            and len(description) + len(brand) + 2 <= 160
        ):
            description = description.rstrip(". ") + f". {brand}."

        return {"title": title, "description": description}

    except Exception as e:
        print(f"Ошибка генерации мета-тегов: {e}")
        return {"title": "", "description": ""}


# === AI КЛИЕНТ ===
@st.cache_resource
def get_groq_client():
    try:
        # Пытаемся взять ключ из настроек сервера (Streamlit Cloud)
        api_key = st.secrets["GROQ_API_KEY"]
    except:
        # Если не нашли (локальный запуск), пробуем из файла .env
        import os

        api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        return None
    return Groq(api_key=api_key)


client = get_groq_client()

# === СОСТОЯНИЕ ===
if "view" not in st.session_state:
    st.session_state.view = "projects"
if "current_project" not in st.session_state:
    st.session_state.current_project = None
if "editing_project" not in st.session_state:
    st.session_state.editing_project = None
if "gen_state" not in st.session_state:
    st.session_state.gen_state = {
        "topics": [],
        "selected_topic": None,
        "meta_tags": {},
        "article_html": "",
        "image_prompts": "",
        "final_prompt": "",
    }


# === СТРАНИЦА 1: ВЫБОР ПРОЕКТА ===
def render_project_selector():
    st.title("📁 Выберите или создайте проект")
    st.markdown("*Каждый проект имеет свою базу знаний и настройки*")

    projects = load_projects()

    if st.button("➕ Добавить новый проект", type="primary", use_container_width=True):
        st.session_state.editing_project = None
        st.session_state.view = "editor"
        st.rerun()

    if not projects:
        st.info("Пока нет проектов. Создайте первый!")
        return

    st.divider()
    st.subheader("Ваши проекты:")

    cols = st.columns(3)
    for i, proj in enumerate(projects):
        with cols[i % 3]:
            with st.container(border=True):
                st.markdown(f"### {proj['name']}")
                st.caption(f"🌐 {proj['domain']}")
                st.caption(f"📦 Ниша: {proj['niche'][:40]}...")
                ex_count = len(load_project_examples(proj["id"]))
                st.caption(f"📚 Примеров: {ex_count}")

                if st.button(
                    "🚀 Открыть", key=f"open_{proj['id']}", use_container_width=True
                ):
                    st.session_state.current_project = proj
                    st.session_state.view = "generator"
                    st.session_state.gen_state = {
                        "topics": [],
                        "selected_topic": None,
                        "meta_tags": {},
                        "article_html": "",
                        "image_prompts": "",
                        "final_prompt": "",
                    }
                    st.rerun()

                if st.button("✏️ Изменить", key=f"edit_{proj['id']}", type="secondary"):
                    st.session_state.editing_project = proj
                    st.session_state.view = "editor"
                    st.rerun()


# === СТРАНИЦА 2: РЕДАКТОР ПРОЕКТА ===
def render_project_editor():
    proj = st.session_state.editing_project
    is_new = proj is None

    st.title(
        "✏️ " + ("Создание нового проекта" if is_new else "Редактирование проекта")
    )

    with st.form("project_form"):
        name = st.text_input("Название проекта", value=proj.get("name", "") if proj else "")
        domain = st.text_input("Домен", value=proj.get("domain", "https://") if proj else "https://")
        niche = st.text_area("Специализация / Ниша", value=proj.get("niche", "") if proj else "", height=80)
        brand = st.text_input("Бренд", value=proj.get("brand", proj.get("name", "")) if proj else "")  # ← НОВОЕ ПОЛЕ

        col1, col2 = st.columns(2)
        with col1:
            submitted = st.form_submit_button("💾 Сохранить", type="primary", use_container_width=True)
        with col2:
            if st.form_submit_button("🔙 Назад к списку", use_container_width=True):
                st.session_state.view = "projects"
                st.rerun()

        if submitted:
            if not name or not domain:
                st.error("Заполните название и домен")
            else:
                if is_new:
                    new_proj = create_project(name, domain, niche, brand)
                    st.session_state.current_project = new_proj
                else:
                    proj.update({"name": name, "domain": domain, "niche": niche, "brand": brand})  # ← СОХРАНЯЕМ БРЕНД
                    update_project(proj)
                    st.session_state.current_project = proj
                st.session_state.view = "generator"
                st.rerun()


# === СТРАНИЦА 3: ГЕНЕРАТОР ===
def render_generator():
    proj = st.session_state.current_project
    if not proj:
        st.session_state.view = "projects"
        st.rerun()

    gs = st.session_state.gen_state

    # === ОТОБРАЖЕНИЕ НАЗВАНИЯ ПРОЕКТА ===
    st.header(f"🏢 {proj['name']}")
    st.caption(f"🌐 {proj['domain']} | 📦 {proj['niche']}")
    st.divider()

    # Боковая панель
    with st.sidebar:
        st.header("⚙️ Настройки проекта")

        # Кнопка редактирования проекта
        if st.button(
            "✏️ Редактировать проект", use_container_width=True, type="secondary"
        ):
            st.session_state.editing_project = proj
            st.session_state.view = "editor"
            st.rerun()

        if st.button("🔙 Сменить проект", use_container_width=True):
            st.session_state.view = "projects"
            st.session_state.current_project = None
            st.rerun()

        st.divider()
        # В боковой панели, раздел загрузки примеров:

        st.subheader("📚 База знаний проекта")
        examples = load_project_examples(proj["id"])
        st.write(f"Сохранено кейсов: **{len(examples)}**")

        # Загрузка примеров с уникальным ключом
        if "upload_counter" not in st.session_state:
            st.session_state.upload_counter = 0

        uploaded_file = st.file_uploader(
            "📤 Загрузить пример",
            type=["json"],
            help="Загрузите JSON файл с примером статьи",
            key=f"upload_{proj['id']}_{st.session_state.upload_counter}",
            label_visibility="collapsed",  # Скрываем лейбл, если нужно
        )

        if uploaded_file is not None:
            try:
                import json

                example_data = json.load(uploaded_file)

                # Сохраняем в папку проекта
                save_project_example(
                    proj["id"],
                    example_data.get("topic", "Imported"),
                    example_data.get("anchor", ""),
                    example_data.get("article_snippet", ""),
                    example_data.get("prompt_snippet", ""),
                )

                # Увеличиваем счётчик для смены ключа uploader'а
                st.session_state.upload_counter += 1

                st.success("✅ Пример загружен!")
                st.balloons()  # Эффект успеха

                # Принудительный rerun с новым ключом uploader'а
                st.rerun()

            except Exception as e:
                st.error(f"Ошибка загрузки: {str(e)[:100]}")
                # Также увеличиваем счётчик при ошибке
                st.session_state.upload_counter += 1
                st.rerun()

        st.divider()
        st.subheader("🔗 Анкорные ссылки")
        if st.button("+ Добавить анкор", key="add_anchor"):
            proj["anchors"].append({"anchor": "", "url": ""})
            update_project(proj)
            st.rerun()

        # Исправленное отображение анкоров
        for i, a in enumerate(proj["anchors"]):
            col_anchor, col_url, col_delete = st.columns([5, 5, 2])  # Фиксированные пропорции
            with col_anchor:
                a["anchor"] = st.text_input(
                    f"Анкор {i+1}",
                    value=a["anchor"],
                    key=f"a{i}_anchor",
                    label_visibility="collapsed",
                )
            with col_url:
                a["url"] = st.text_input(
                    f"URL {i+1}",
                    value=a["url"],
                    key=f"a{i}_url",
                    label_visibility="collapsed",
                )
            with col_delete:
                if st.button("❌", key=f"d{i}", help="Удалить"):
                    proj["anchors"].pop(i)
                    update_project(proj)
                    st.rerun()
        update_project(proj)

    # Валидация анкоров
    anchors_list = [a["anchor"] for a in proj["anchors"] if a["anchor"]]
    if not anchors_list:
        st.info("👉 Добавьте хотя бы один анкор в боковой панели")
        st.stop()

    selected_anchor = st.selectbox("🎯 Выберите анкор:", anchors_list)
    current_url = next(
        a["url"] for a in proj["anchors"] if a["anchor"] == selected_anchor
    )
    st.subheader(f"📌 Анкор: `{selected_anchor}`")

        # ШАГ 1: ТЕМЫ (УЛУЧШЕННЫЙ ПРОМПТ)
    st.markdown("### Шаг 1: Выбор темы")
    if st.button("🔍 Сгенерировать 5 тем", type="primary", key="gen_topics"):
        with st.spinner("🤖 AI анализирует нишу..."):
            example_topics = """
    ПРИМЕРЫ ОТЛИЧНЫХ КОММЕРЧЕСКИХ ТЕМ:
    • Автоцистерны для питьевой и технической воды: в чём разница и как не нарушить СанПиН?
    • Как быстро купить спецтехнику в Миассе: готовые ППУА в наличии или под заказ?
    • ППУА для промывки скважин: как выбрать установку под тип месторождения?
    • Что входит в гарантию и сервисное обслуживание ППУА от завода-производителя?
    • Можно ли дооснастить ППУА на шасси дополнительным оборудованием (БРС, газовая горелка, автоматика)?
    • Обработка скважин соляной кислотой: требования к оборудованию и безопасности
    • Как правильно укомплектовать передвижную мастерскую: чек-лист оборудования для разных задач

    ПАТТЕРНЫ УСПЕШНЫХ ТЕМ:
    1. [Продукт]: в чём разница между А и Б / как не нарушить [норму]
    2. Как быстро [действие]: [вариант 1] или [вариант 2]?
    3. [Продукт] для [задача]: как выбрать под [критерий]?
    4. Что входит в [услуга] от [источник]?
    5. Можно ли [модификация] с [доп. оборудование]?
    6. [Процесс]: требования к [оборудование] и [безопасность]
    7. Как правильно [действие]: чек-лист для [задачи]
    """
            prompt = f"""Ты опытный копирайтер для B2B-сегмента (промышленность, спецтехника, нефтегаз).

    ПРОЕКТ: {proj['name']}
    ДОМЕН: {proj['domain']}
    НИША: {proj['niche']}
    КЛЮЧЕВОЙ ЗАПРОС (АНКОР): {selected_anchor}

    {example_topics}

    ЗАДАЧА: Подбери ровно 5 КОММЕРЧЕСКИХ тем для статьи.

    ТРЕБОВАНИЯ К ТЕМАМ:
    ✅ Формат: вопрос или утверждение с двоеточием (как в примерах выше)
    ✅ Коммерческий интент: покупка, выбор, сравнение, сроки, цены, гарантия, модификация
    ✅ Конкретика: упоминай типы оборудования, нормативы (ГОСТ, СанПиН), локации, задачи
    ✅ Длина: 60-120 символов
    ✅ Без воды: никаких "Введение в...", "Общая информация о..."
    ✅ Решают проблему бизнеса: помогают выбрать, ускорить, сэкономить, обезопасить

    ФОРМАТ ВЫВОДА СТРОГО:
    1. Полная тема один
    2. Полная тема два
    3. Полная тема три
    4. Полная тема четыре
    5. Полная тема пять

    Выведи только список, без пояснений."""

            try:
                resp = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.8,
                    max_tokens=400,
                )
                raw = resp.choices[0].message.content.strip()

                topics = []
                for line in raw.split("\n"):
                    line = line.strip()
                    if line and line[0].isdigit() and ". " in line:
                        topic = line.split(". ", 1)[1].strip()
                        if topic and 30 < len(topic) < 150:
                            topics.append(topic)

                gs["topics"] = topics[:5]
                gs["selected_topic"] = None
                st.rerun()
            except Exception as e:
                st.error(f"Ошибка: {str(e)[:100]}")

    # === ОТОБРАЖЕНИЕ ТЕМ И ВЫБОР ===
    if gs["topics"]:
        st.markdown("**Выберите тему:**")
        for i, t in enumerate(gs["topics"], 1):
            if st.button(f"📌 {i}. {t}", key=f"sel_{i}", use_container_width=True):
                gs["selected_topic"] = t

                # ГЕНЕРАЦИЯ МЕТА-ТЕГОВ
                with st.spinner("🏷️ Генерирую мета-теги..."):
                    gs["meta_tags"] = generate_meta_tags(
                        topic=t,
                        anchor=selected_anchor,
                        niche=proj["niche"],
                        domain=proj["domain"],
                        brand = proj.get("brand", proj["name"]),
                        client=client,
                    )

                # СОХРАНЕНИЕ "ЗОЛОТОЙ ТЕМЫ" (отдельно, после генерации)
                try:
                    with open(DATA_DIR / "golden_topics.json", "a", encoding="utf-8") as f:
                        json.dump(
                            {
                                "topic": gs["selected_topic"],
                                "anchor": selected_anchor,
                                "project": proj["id"],
                                "timestamp": datetime.now().isoformat(),
                            },
                            f,
                            ensure_ascii=False,
                        )
                        f.write("\n")
                except:
                    pass  # Игнорируем ошибки сохранения

                st.success(f"✅ Выбрана: {t}")
                st.rerun()

    # === ОТОБРАЖЕНИЕ МЕТА-ТЕГОВ (ОТДЕЛЬНЫЙ БЛОК!) ===
    # Этот блок выполняется, когда мета-теги уже сгенерированы
    if gs.get("meta_tags") and gs["meta_tags"].get("title") and gs.get("selected_topic"):
        st.divider()
        st.markdown("### 🏷️ SEO Мета-теги")

        meta = gs["meta_tags"]

        col1, col2 = st.columns(2)
        with col1:
            st.info(f"**Title** ({len(meta['title'])} симв.)\n\n{meta['title']}")
        with col2:
            st.info(
                f"**Description** ({len(meta['description'])} симв.)\n\n{meta['description']}"
            )

        if st.button("🔄 Перегенерировать мета-теги", type="secondary"):
            with st.spinner("Генерация..."):
                gs["meta_tags"] = generate_meta_tags(
                    topic=gs["selected_topic"],
                    anchor=selected_anchor,
                    niche=proj["niche"],
                    domain=proj["domain"],
                    client=client,
                )
                st.rerun()

        st.divider()

    # ШАГ 2: СТАТЬЯ
    if gs["selected_topic"]:
        st.divider()
        st.markdown("### Шаг 2: Генерация статьи")
        if st.button("✍️ Сгенерировать статью", type="primary", key="gen_art"):
            with st.spinner("🤖 Пишем статью... (2-3 мин)"):
                ex = find_similar_example(
                    gs["selected_topic"],
                    selected_anchor,
                    load_project_examples(proj["id"]),
                )
                few_shot = (
                    f"\n📚 ПРИМЕР УСПЕШНОЙ СТАТЬИ:\nТема: {ex['topic']}\nФрагмент: {ex['article_snippet']}..."
                    if ex
                    else ""
                )

                sys_prompt = f"""Ты профессиональный SEO-копирайтер B2B.
НИША: {proj['niche']}
ТРЕБОВАНИЯ:
1. Структура: H1, 5-7 H2, боль клиента, таблица, CTA, FAQ (8 вопросов)
2. Стиль: коммерческий, конкретика (цифры, сроки, выгоды), без воды
3. Формат: чистый HTML (<h1><h2><p><ul><li><strong><table>)
4. Объём: 10000-14000 знаков
5. Естественно вписывай ключи{few_shot}
Выведи ТОЛЬКО HTML-код."""

                try:
                    resp = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[
                            {"role": "system", "content": sys_prompt},
                            {
                                "role": "user",
                                "content": f"Тема: {gs['selected_topic']}\nАнкор: {selected_anchor}\nСайт: {proj['domain']}",
                            },
                        ],
                        temperature=0.7,
                        max_tokens=4000,
                    )
                    gs["article_html"] = resp.choices[0].message.content.strip()
                    st.rerun()
                except Exception as e:
                    st.error(f"Ошибка: {str(e)[:100]}")

        if gs["article_html"]:
            with st.expander("👁️ Предпросмотр статьи"):
                st.code(gs["article_html"][:800] + "...", language="html")

            if st.button("💾 Сохранить в базу знаний проекта", type="secondary"):
                save_project_example(
                    proj["id"],
                    gs["selected_topic"],
                    selected_anchor,
                    gs["article_html"],
                    "article_gen_prompt",
                )
                st.success("✅ Сохранено! AI запомнит стиль этого проекта.")
                # Показываем что сохранилось
                with st.expander("👁️ Что сохранено"):
                    st.write(f"**Тема:** {gs['selected_topic']}")
                    st.write(f"**Анкор:** {selected_anchor}")
                    st.write(f"**Длина статьи:** {len(gs['article_html'])} симв.")
                    if gs["final_prompt"]:
                        st.write(
                            f"**Финальный промпт:** {len(gs['final_prompt'])} симв."
                        )

            # ШАГ 3: КАРТИНКИ
    if gs["article_html"]:
        st.divider()
        st.markdown("### Шаг 3: Промпты для изображений")

        if st.button(
            "🎨 Сгенерировать 4 промпта", type="primary", key=f"gen_imgs_{proj['id']}"
        ):
            with st.spinner("🎨 Генерация..."):
                prompt = f"""Ты промпт-инженер. Тема: {gs['selected_topic']}. Ключ: {selected_anchor}.
    Создай 4 промпта. Требования: 16:9, фотореализм, без текста, славянская внешность, контекст: {proj['niche']}.
    ФОРМАТ:
    Промпт №1 — [Название]
    Концепция: [описание на русском]
    [English prompt]
    Промпт №2 — ..."""
                try:
                    resp = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.7,
                        max_tokens=1200,  # Увеличили
                    )
                    raw_prompts = resp.choices[0].message.content.strip()

                    if not raw_prompts or len(raw_prompts) < 50:
                        st.error("⚠️ Пустой ответ от AI. Попробуйте ещё раз.")
                    else:
                        gs["image_prompts"] = raw_prompts
                        st.success("✅ Промпты готовы!")
                        st.rerun()
                except Exception as e:
                    st.error(f"❌ Ошибка: {str(e)[:100]}")

        # Отображение промптов (исправленное условие)
        if gs.get("image_prompts") and len(gs["image_prompts"]) > 10:
            st.code(gs["image_prompts"], language="text")

            # ШАГ 4: ФИНАЛЬНЫЙ ПРОМПТ
            st.divider()
            st.markdown("### Шаг 4: Финальный экспорт")

            cols = st.columns(4)
            img_urls = [
                st.text_input(
                    f"Img {i+1}",
                    value=f"https://i.postimg.cc/ex{i+1}.png",
                    key=f"im{i}_{proj['id']}",
                )
                for i in range(4)
            ]

            if st.button(
                "📄 Собрать финальный промпт", type="primary", key=f"final_{proj['id']}"
            ):
                final = f"""У меня есть готовая статья в формате html.
    Не меняя ничего в тексте статьи и не сокращая её (это важно!), добавь эти четыре изображения,
    {chr(10).join(img_urls)}
    Первое изображение должно стоять в самом начале статьи перед текстом, остальные изображения размести в неё равномерно по тексту.
    Изображения должны иметь alt = {selected_anchor} и размером 100% по ширине.
    Начинаться статья должна с ключевой фразы - {selected_anchor}. Далее логично продолжай.
    Убери теги <b> и </b>. В абзацах расставь переносы строки после 2-3 предложений.
    Используй ключи: {selected_anchor}, {proj['name']}, {proj['domain'].replace('https://','')}
    Сделай по теме «{gs['selected_topic']}» таблицу и размести логично.
    Сделай диаграмму на https://quickchart.io и размести логично.
    Добавь фразу "Специалисты {proj['name']} считают, что" и заверши предложение.
    Добавь FAQ (8 вопросов, 3 из People Also Ask).
    Оцени объём: если <10000 знаков - дополни, если >14000 - сократи.
    Получи статью 10000-14000 знаков в HTML с картинками, таблицей, диаграммой, упоминанием компании и FAQ.
    Вот сама статья:
    <article>
    {gs['article_html']}
    </article>"""
                gs["final_prompt"] = final
                st.rerun()

            if gs.get("final_prompt"):
                st.code(gs["final_prompt"], language="text")

                if st.button(
                    "💾 Сохранить в базу знаний проекта",
                    type="primary",
                    key=f"save_{proj['id']}",
                ):
                    save_project_example(
                        proj["id"],
                        gs["selected_topic"],
                        selected_anchor,
                        gs["article_html"],
                        gs["final_prompt"],
                    )
                    st.success("✅ Сохранено!")

                st.download_button(
                    "⬇️ Скачать .txt",
                    data=gs["final_prompt"],
                    file_name=f"prompt_{datetime.now().strftime('%m%d_%H%M')}.txt",
                    mime="text/plain",
                )


# === РОУТИНГ ===
if st.session_state.view == "projects":
    render_project_selector()
elif st.session_state.view == "editor":
    render_project_editor()
elif st.session_state.view == "generator":
    render_generator()
