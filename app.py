import streamlit as st
import os
import json
from groq import Groq
from datetime import datetime
from pathlib import Path
from difflib import SequenceMatcher
from supabase import create_client, Client
import uuid

# === ГЛОБАЛЬНЫЕ СТИЛИ ===
st.markdown(
    """
<style>
/* Основной цвет кнопок - красивый синий/фиолетовый */
.stButton > button {
    background-color: #667eea !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    padding: 0.5rem 1rem !important;
    font-weight: 500 !important;
    transition: all 0.3s ease !important;
}
.stButton > button:hover {
    background-color: #5a6fd6 !important;
    transform: translateY(-1px);
    box-shadow: 0 4px 8px rgba(102, 126, 234, 0.3);
}
.stButton > button:active {
    transform: translateY(0);
}

/* Второстепенные кнопки - прозрачные с рамкой */
.stButton > button[kind="secondary"] {
    background-color: transparent !important;
    color: #667eea !important;
    border: 1px solid #667eea !important;
}
.stButton > button[kind="secondary"]:hover {
    background-color: rgba(102, 126, 234, 0.1) !important;
}

/* Кнопка удаления - красная */
.delete-btn > button {
    background-color: #ff4b4b !important;
    color: white !important;
}

/* Убираем лишние отступы */
.block-container {
    padding-top: 2rem;
    padding-bottom: 2rem;
}
</style>
""",
    unsafe_allow_html=True,
)

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
    import random

    # Генерация случайного градиента для проекта
    gradients = [
        ("#667eea", "#764ba2"),  # Фиолетовый
        ("#f093fb", "#f5576c"),  # Розовый
        ("#4facfe", "#00f2fe"),  # Голубой
        ("#43e97b", "#38f9d7"),  # Зелёный
        ("#fa709a", "#fee140"),  # Оранжево-розовый
        ("#30cfd0", "#330867"),  # Тёмно-синий
        ("#a8edea", "#fed6e3"),  # Пастельный
        ("#ff9a9e", "#fecfef"),  # Светло-розовый
        ("#ffecd2", "#fcb69f"),  # Персиковый
        ("#667eea", "#764ba2"),  # Повтор фиолетового
    ]

    # Выбираем случайный градиент
    color1, color2 = random.choice(gradients)

    pid = name.lower().replace(" ", "_").replace("-", "_")[:20]
    project = {
        "id": pid,
        "name": name,
        "domain": domain,
        "brand": brand if brand else name,
        "niche": niche,
        "anchors": [],
        "noanchors": [],
        "gradient_start": color1,  # ← ДОБАВИТЬ!
        "gradient_end": color2,  # ← ДОБАВИТЬ!
        "created_at": datetime.now().isoformat(),
    }
    projects = load_projects()
    projects.append(project)
    save_projects(projects)
    (EXAMPLES_ROOT / pid).mkdir(exist_ok=True)
    return project


def update_project(updated: dict):
    import random

    gradients = [
        ("#667eea", "#764ba2"),
        ("#f093fb", "#f5576c"),
        ("#4facfe", "#00f2fe"),
        ("#43e97b", "#38f9d7"),
        ("#fa709a", "#fee140"),
        ("#30cfd0", "#330867"),
        ("#a8edea", "#fed6e3"),
        ("#ff9a9e", "#fecfef"),
        ("#ffecd2", "#fcb69f"),
    ]

    projects = load_projects()
    for i, p in enumerate(projects):
        if p["id"] == updated["id"]:
            # Если у проекта нет цвета, назначаем случайный
            if "gradient_start" not in updated:
                color1, color2 = random.choice(gradients)
                updated["gradient_start"] = color1
                updated["gradient_end"] = color2
            projects[i] = updated
            break
    save_projects(projects)


# === УТИЛИТЫ: ПРИМЕРЫ ===
def get_project_examples_dir(pid: str) -> Path:
    d = EXAMPLES_ROOT / pid
    d.mkdir(exist_ok=True)
    return d


# === SUPABASE КЛИЕНТ ===
@st.cache_resource
def get_supabase_client():
    try:
        return create_client(
            st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_ANON_KEY"]
        )
    except:
        return None


supabase_client = get_supabase_client()


# === ХЕДЕР И ФУТЕР ===
def render_header(current_project=None):
    """Отображает верхнюю панель навигации"""
    ai_status = "✅ AI Online" if client else "⚠️ AI Offline"
    db_status = "✅ Supabase" if supabase_client else "💾 Local"

    html = f"""
    <div style="
        display: flex; justify-content: space-between; align-items: center;
        padding: 14px 20px; background: #ffffff;
        border-bottom: 1px solid #e8e8e8; margin-bottom: 24px;
        border-radius: 0 0 12px 12px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.04);
    ">
        <div style="display: flex; align-items: center; gap: 14px;">
            <div style="font-size: 1.45em; font-weight: 700; color: #1a1a1a; line-height: 1.2;">
                SEO Article Generator
            </div>    
        </div>
        <div style="display: flex; gap: 10px; align-items: center;">
            <span style="padding: 5px 12px; background: #e8f5e9; color: #2e7d32; border-radius: 20px; font-size: 0.8em; font-weight: 500;">
                {ai_status}
            </span>
            <span style="padding: 5px 12px; background: #e3f2fd; color: #1565c0; border-radius: 20px; font-size: 0.8em; font-weight: 500;">
                {db_status}
            </span>
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def render_footer():
    """Отображает нижний колонтитул"""
    html = """
    <div style="
        margin-top: 60px; padding: 28px 0 20px 0;
        border-top: 1px solid #e8e8e8; text-align: center;
        color: #888; font-size: 0.85em; line-height: 1.7;
    ">
        <div style="font-weight: 600; color: #555; margin-bottom: 6px;">
            SEO Article Generator Pro v1.2
        </div>
        <div style="color: #999;">
            Powered by Llama 3.3 • Supabase • Streamlit
        </div><!--
        <div style="margin-top: 14px;">
            <a href="#" style="color: #667eea; text-decoration: none; margin: 0 10px; font-weight: 500;">Документация</a>
            <span style="color: #ddd;">•</span>
            <a href="#" style="color: #667eea; text-decoration: none; margin: 0 10px; font-weight: 500;">Поддержка</a>
            <span style="color: #ddd;">•</span>
            <a href="#" style="color: #667eea; text-decoration: none; margin: 0 10px; font-weight: 500;">GitHub</a>
        </div>
        <div style="margin-top: 12px; font-size: 0.8em; color: #aaa;">
            © 2026 SEO Article Generator. Все права защищены.
        </div>-->
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


# === УТИЛИТЫ: ПРИМЕРЫ (ОБЛАЧНЫЕ) ===
def load_project_examples(pid: str):
    if not supabase_client:
        return []  # Фоллбэк, если Supabase не подключён
    resp = (
        supabase_client.table("examples")
        .select("*")
        .eq("project_id", pid)
        .order("created_at", desc=True)
        .execute()
    )
    return resp.data or []


def save_project_example(
    pid: str, topic: str, anchor: str, article_snippet: str, prompt_snippet: str
):
    if not supabase_client:
        return "offline"
    supabase_client.table("examples").insert(
        {
            "project_id": pid,
            "topic": topic,
            "anchor": anchor,
            "article_snippet": article_snippet[:500],
            "prompt_snippet": prompt_snippet[:500],
        }
    ).execute()
    return "saved"


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
    """Генерирует SEO Title и Description (улучшенная версия)"""

    prompt = f"""Ты профессиональный SEO-специалист для B2B (промышленность, спецтехника).

ЗАДАЧА: Создай мета-теги для статьи.

ТЕМА: {topic}
КЛЮЧ: {anchor}
НИША: {niche}
БРЕНД: {brand}
ДОМЕН: {domain}

ПРИМЕРЫ ОТЛИЧНЫХ TITLE:
• Автоцистерна для питьевой воды — требования по СанПиН
• Купить ППУА в Миассе — в наличии или под заказ
• Как выбрать ППУА для промывки скважин под месторождение
• Гарантия и сервис ППУА от завода-производителя
• Дооснащение ППУА: БРС, газовая горелка, автоматика
• Обработка скважин кислотой: требования к оборудованию | Unisteam

ПАТТЕРНЫ:
1. [Продукт] — [Требование/Норма]
2. [Действие] [Продукт] — [Варианты]
3. Как [выбрать/купить] [продукт] для [задача]
4. [Услуга] от [источник]
5. [Модификация]: [список]
6. [Процесс]: требования к [оборудование] | [Бренд]

ТРЕБОВАНИЯ К TITLE:
✅ 50-65 символов (с пробелами)
✅ Ключ в начале или середине
✅ Коммерческий интент
✅ Можно добавить " | {brand}" в конце
✅ ЗАКАНЧИВАТЬ НА ПОЛНОМ СЛОВЕ

ТРЕБОВАНИЯ К DESCRIPTION:
✅ 140-160 символов
✅ Конкретика: цифры, сроки, нормативы
✅ Упоминание бренда в конце: "{brand}."
✅ ЗАКАНЧИВАТЬ НА ПОЛНОМ СЛОВЕ

ФОРМАТ:
Title: [ваш текст]
Description: [ваш текст]"""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,  # Меньше случайности для точности
            max_tokens=200,
        )
        raw = response.choices[0].message.content.strip()

        title = ""
        description = ""

        if "Title:" in raw and "Description:" in raw:
            title = raw.split("Title:")[1].split("Description:")[0].strip()
            description = raw.split("Description:")[1].strip()

        # Умная обрезка
        def smart_truncate(text, max_length):
            if len(text) <= max_length:
                return text.strip()
            truncated = text[:max_length].rstrip()
            while truncated and truncated[-1] in " ,;:.-!?":
                truncated = truncated[:-1]
            last_space = truncated.rfind(" ")
            if last_space > max_length * 0.7:
                return truncated[:last_space].strip()
            return truncated.strip()

        title = smart_truncate(title, 65)
        description = smart_truncate(description, 160)

        if (
            brand.lower() not in description.lower()
            and len(description) + len(brand) + 2 <= 160
        ):
            description = description.rstrip(". ") + f". {brand}."

        return {"title": title, "description": description}
    except Exception as e:
        print(f"Ошибка: {e}")
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
    render_header()
    st.title("Выберите или создайте проект")
    st.markdown("*Каждый проект имеет свою базу знаний и настройки*")

    # 2. Кнопка на всю ширину
    if st.button("Добавить новый проект", type="primary", use_container_width=True):
        st.session_state.editing_project = None
        st.session_state.view = "editor"
        st.rerun()

    projects = load_projects()

    if not projects:
        st.info("Пока нет проектов. Создайте первый!")
        return

    st.markdown("---")
    st.subheader("Ваши проекты:")

    cols = st.columns(3)
    for i, proj in enumerate(projects):
        with cols[i % 3]:
            color1 = proj.get("gradient_start", "#667eea")
            color2 = proj.get("gradient_end", "#764ba2")

            with st.container(border=True):
                st.markdown(
                    f"""
                    <div style="
                        background: linear-gradient(135deg, {color1} 0%, {color2} 100%);
                        padding: 20px; 
                        border-radius: 12px;
                        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                        margin-bottom: 15px;
                        text-align: center;">
                        <h3 style="color: white; margin: 0; font-size: 1.5em; font-weight: 700;">
                            {proj['name']}
                        </h3>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                st.caption(f"Домен: {proj['domain']}")
                st.caption(f"Ниша: {proj['niche'][:45]}...")

                ex_count = len(load_project_examples(proj["id"]))
                st.caption(f"Примеров: {ex_count}")

                st.markdown("<br>", unsafe_allow_html=True)

                if st.button(
                    "Открыть",
                    key=f"open_{proj['id']}",
                    use_container_width=True,
                    type="primary",
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

                if st.button(
                    "Изменить", key=f"edit_{proj['id']}", use_container_width=True
                ):
                    st.session_state.editing_project = proj
                    st.session_state.view = "editor"
                    st.rerun()
    render_footer()


# === СТРАНИЦА 2: РЕДАКТОР ПРОЕКТА ===
def render_project_editor():
    render_header()
    proj = st.session_state.editing_project
    is_new = proj is None

    # 1. Убрали стикер 📝
    st.title("Редактирование проекта" if not is_new else "Создание нового проекта")

    with st.form("project_form"):
        name = st.text_input(
            "Название проекта", value=proj.get("name", "") if proj else ""
        )
        domain = st.text_input(
            "Домен", value=proj.get("domain", "https://") if proj else "https://"
        )
        niche = st.text_area(
            "Специализация / Ниша",
            value=proj.get("niche", "") if proj else "",
            height=80,
        )
        brand = st.text_input(
            "Бренд", value=proj.get("brand", proj.get("name", "")) if proj else ""
        )

        # === НАСТРОЙКА ЦВЕТА ПРОЕКТА ===
        st.markdown("---")
        st.markdown("#### Цвет проекта")

        # Получаем текущие цвета или дефолтные
        current_color1 = proj.get("gradient_start", "#667eea") if proj else "#667eea"
        current_color2 = proj.get("gradient_end", "#764ba2") if proj else "#764ba2"

        col_c1, col_c2 = st.columns(2)
        with col_c1:
            color1 = st.color_picker(
                "Начальный цвет",
                value=current_color1,
                key="color1_picker",
                help="Цвет в начале градиента",
            )
        with col_c2:
            color2 = st.color_picker(
                "Конечный цвет",
                value=current_color2,
                key="color2_picker",
                help="Цвет в конце градиента",
            )

        # Превью градиента
        st.markdown(
            f"""
            <div style="
                background: linear-gradient(135deg, {color1} 0%, {color2} 100%);
                height: 40px; 
                border-radius: 8px; 
                margin: 10px 0;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            "></div>
            """,
            unsafe_allow_html=True,
        )

        col1, col2, col3 = st.columns([3, 3, 3])
        with col1:
            submitted = st.form_submit_button(
                "Сохранить", type="primary", use_container_width=True
            )
        with col2:
            if st.form_submit_button("Назад", use_container_width=True):
                st.session_state.view = "projects"
                st.rerun()
        with col3:
            # 2. Кнопка удаления проекта (только для существующих)
            if not is_new:
                if st.form_submit_button(
                    "Удалить проект",
                    use_container_width=True,
                    help="Это действие нельзя отменить",
                ):
                    # Удаляем проект из списка
                    projects = load_projects()
                    projects = [p for p in projects if p["id"] != proj["id"]]
                    save_projects(projects)

                    # Опционально: удаляем папку примеров
                    import shutil

                    if (EXAMPLES_ROOT / proj["id"]).exists():
                        shutil.rmtree(EXAMPLES_ROOT / proj["id"])

                    st.session_state.view = "projects"
                    st.session_state.current_project = None
                    st.rerun()

    if submitted:
        if not name or not domain:
            st.error("Заполните название и домен")
        else:
            if is_new:
                new_proj = create_project(name, domain, niche, brand)
                new_proj.update({"gradient_start": color1, "gradient_end": color2})
                update_project(new_proj)
                st.session_state.current_project = new_proj
            else:
                proj.update({
                    "name": name, "domain": domain, "niche": niche, "brand": brand,
                    "gradient_start": color1, "gradient_end": color2
                })
                update_project(proj)
                st.session_state.current_project = proj
            st.session_state.view = "generator"
            st.rerun()           
    render_footer()


# === СТРАНИЦА 3: ГЕНЕРАТОР ===
def render_generator():
    render_header()
    proj = st.session_state.current_project
    if not proj:
        st.session_state.view = "projects"
        st.rerun()

    gs = st.session_state.gen_state

    # === ОТОБРАЖЕНИЕ НАЗВАНИЯ ПРОЕКТА ===
    color1 = proj.get("gradient_start", "#667eea")
    color2 = proj.get("gradient_end", "#764ba2")

    st.markdown(
        f"""
        <div style="background: linear-gradient(135deg, {color1} 0%, {color2} 100%); 
                    padding: 40px; border-radius: 16px; margin-bottom: 30px; 
                    box-shadow: 0 8px 16px rgba(0,0,0,0.15);">
            <h1 style="color: white; margin: 0; font-size: 2.8em; font-weight: 700;">
                {proj['name']}
            </h1>
            <p style="color: rgba(255,255,255,0.95); margin: 12px 0 0 0; font-size: 1.2em; line-height: 1.6;">
                {proj['domain']}
            </p>
            <p style="color: rgba(255,255,255,0.85); margin: 8px 0 0 0; font-size: 1.1em;">
                {proj['niche']}
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Боковая панель
    with st.sidebar:
        # Заголовок без style параметра
        st.markdown(
            """
        <div style="margin-top: 20px;">
            <h3 style="margin: 0 0 15px 0; font-size: 1.2em; color: #2c3e50;">Настройки проекта</h3>
        </div>
        """,
            unsafe_allow_html=True,
        )

        if st.button(
            "Редактировать проект", use_container_width=True, type="secondary"
        ):
            st.session_state.editing_project = proj
            st.session_state.view = "editor"
            st.rerun()

        if st.button("Сменить проект", use_container_width=True):
            st.session_state.view = "projects"
            st.session_state.current_project = None
            st.rerun()

        st.markdown("---")
        st.markdown("### База знаний проекта")
        examples = load_project_examples(proj["id"])
        st.markdown(f"**Примеров:** {len(examples)}")

        # Загрузка примеров
        if "upload_counter" not in st.session_state:
            st.session_state.upload_counter = 0

        uploaded_file = st.file_uploader(
            "Загрузить пример",
            type=["json"],
            key=f"upload_{proj['id']}_{st.session_state.upload_counter}",
            label_visibility="collapsed",
        )

        if uploaded_file is not None:
            try:
                import json

                example_data = json.load(uploaded_file)
                save_project_example(
                    proj["id"],
                    example_data.get("topic", "Imported"),
                    example_data.get("anchor", ""),
                    example_data.get("article_snippet", ""),
                    example_data.get("prompt_snippet", ""),
                )
                st.session_state.upload_counter += 1
                st.success("Пример загружен!")
                st.rerun()
            except Exception as e:
                st.error(f"Ошибка: {str(e)[:50]}")
                st.session_state.upload_counter += 1
                st.rerun()

        st.markdown("---")
        st.markdown("### Анкорные ссылки")
        if st.button("+ Добавить анкор", key="add_anchor", use_container_width=True):
            proj["anchors"].insert(0, {"anchor": "", "url": ""})
            update_project(proj)
            st.rerun()

        # Отображение анкоров
        for i, a in enumerate(proj["anchors"]):
            cols = st.columns([4, 4, 1])
            with cols[0]:
                a["anchor"] = st.text_input(
                    "Анкор",
                    value=a["anchor"],
                    key=f"a{i}_anchor",
                    label_visibility="collapsed",
                    placeholder="Текст анкора",
                )
            with cols[1]:
                a["url"] = st.text_input(
                    "URL",
                    value=a["url"],
                    key=f"a{i}_url",
                    label_visibility="collapsed",
                    placeholder="https://...",
                )
            with cols[2]:
                if st.button("×", key=f"d{i}", help="Удалить"):
                    proj["anchors"].pop(i)
                    update_project(proj)
                    st.rerun()

        update_project(proj)

        st.markdown("---")
        st.markdown("### Безанкорные ссылки")
        if st.button(
            "+ Добавить безанкор", key="add_noanchor", use_container_width=True
        ):
            proj["noanchors"].insert(0, "")
            update_project(proj)
            st.rerun()

        for i, url in enumerate(proj["noanchors"]):
            cols = st.columns([5, 1])
            with cols[0]:
                proj["noanchors"][i] = st.text_input(
                    f"Безанкор {i+1}",
                    value=url,
                    key=f"na{i}",
                    label_visibility="collapsed",
                    placeholder="https://...",
                )
            with cols[1]:
                if st.button("×", key=f"dn{i}"):
                    proj["noanchors"].pop(i)
                    update_project(proj)
                    st.rerun()
        update_project(proj)

    # Валидация анкоров
    anchors_list = [a["anchor"] for a in proj["anchors"] if a["anchor"]]
    if not anchors_list:
        st.info("Добавьте хотя бы один анкор в боковой панели")
        st.stop()

    selected_anchor = st.selectbox("Выберите анкор:", anchors_list)
    current_url = next(
        a["url"] for a in proj["anchors"] if a["anchor"] == selected_anchor
    )

    st.markdown(f"#### Анкор: `{selected_anchor}`")
    st.markdown(f"*Целевая ссылка:* {current_url}")

    # Поле для своей темы
    st.markdown("---")
    custom_topic = st.text_input(
        "Или введите свою тему:",
        placeholder="Введите тему статьи...",
        key=f"custom_topic_{proj['id']}",
    )

    if custom_topic:
        gs["selected_topic"] = custom_topic
        st.success(f"Тема: {custom_topic}")
        st.markdown("---")

    # ШАГ 1: ТЕМЫ
    st.markdown("### Шаг 1: Выбор темы")
    if st.button("Сгенерировать 5 тем", type="primary", key="gen_topics"):
        with st.spinner("AI анализирует нишу..."):
            example_topics = """
ПРИМЕРЫ КОММЕРЧЕСКИХ ТЕМ:
• Автоцистерны для питьевой и технической воды: в чём разница и как не нарушить СанПиН?
• Как быстро купить спецтехнику в Миассе: готовые ППУА в наличии или под заказ?
• ППУА для промывки скважин: как выбрать установку под тип месторождения?
• Что входит в гарантию и сервисное обслуживание ППУА от завода-производителя?
• Можно ли дооснастить ППУА на шасси дополнительным оборудованием?
• Обработка скважин соляной кислотой: требования к оборудованию и безопасности
• Как правильно укомплектовать передвижную мастерскую: чек-лист оборудования
"""
            prompt = f"""Ты опытный SEO-копирайтер для B2B (промышленность, спецтехника).

ПРОЕКТ: {proj['name']}
ДОМЕН: {proj['domain']}
НИША: {proj['niche']}
КЛЮЧ: {selected_anchor}

{example_topics}

ЗАДАЧА: Подбери 5 КОММЕРЧЕСКИХ тем.

ТРЕБОВАНИЯ:
✅ Формат: вопрос или утверждение с двоеточием
✅ Коммерческий интент: покупка, выбор, сравнение, сроки, цены
✅ Конкретика: нормативы, локации, задачи
✅ Длина: 60-120 символов
✅ Без воды

ФОРМАТ:
1. Тема один
2. Тема два
3. Тема три
4. Тема четыре
5. Тема пять"""

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

    if gs["topics"]:
        st.markdown("**Выберите тему:**")
        for i, t in enumerate(gs["topics"], 1):
            if st.button(f"{i}. {t}", key=f"sel_{i}", use_container_width=True):
                gs["selected_topic"] = t
                # Копирование в буфер обмена
                st.code(t, language="text")
                st.success("Тема скопирована в буфер обмена!")
                st.rerun()

    # ОТОБРАЖЕНИЕ МЕТА-ТЕГОВ С КНОПКАМИ КОПИРОВАНИЯ
    if (
        gs.get("meta_tags")
        and gs["meta_tags"].get("title")
        and gs.get("selected_topic")
    ):
        st.markdown("---")
        st.markdown("### SEO Мета-теги")

        meta = gs["meta_tags"]

        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Title** ({len(meta['title'])} симв.)")
            st.text_area(
                "Title",
                value=meta["title"],
                height=80,
                label_visibility="collapsed",
                key="title_copy",
            )
            st.caption("Нажмите Ctrl+C для копирования")

        with col2:
            st.markdown(f"**Description** ({len(meta['description'])} симв.)")
            st.text_area(
                "Description",
                value=meta["description"],
                height=120,
                label_visibility="collapsed",
                key="desc_copy",
            )
            st.caption("Нажмите Ctrl+C для копирования")

        if st.button("Перегенерировать мета-теги", type="secondary"):
            with st.spinner("Генерация..."):
                gs["meta_tags"] = generate_meta_tags(
                    topic=gs["selected_topic"],
                    anchor=selected_anchor,
                    niche=proj["niche"],
                    domain=proj["domain"],
                    brand=proj.get("brand", proj["name"]),
                    client=client,
                )
                st.rerun()

        st.markdown("---")

    # ШАГ 2: СТАТЬЯ
    if gs["selected_topic"]:
        st.markdown("### Шаг 2: Генерация статьи")
        if st.button("Сгенерировать статью", type="primary", key="gen_art"):
            with st.spinner("Пишем статью..."):
                ex = find_similar_example(
                    gs["selected_topic"],
                    selected_anchor,
                    load_project_examples(proj["id"]),
                )
                few_shot = (
                    f"\nПРИМЕР УСПЕШНОЙ СТАТЬИ:\nТема: {ex['topic']}\nФрагмент: {ex['article_snippet']}..."
                    if ex
                    else ""
                )

                sys_prompt = f"""Ты профессиональный SEO-копирайтер B2B.
НИША: {proj['niche']}
ТРЕБОВАНИЯ:
1. Структура: H1, 5-7 H2, таблица, FAQ
2. Стиль: коммерческий, конкретика
3. Формат: чистый HTML
4. Объём: 10000-14000 знаков{few_shot}
Выведи ТОЛЬКО HTML-код."""

                try:
                    resp = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[
                            {"role": "system", "content": sys_prompt},
                            {
                                "role": "user",
                                "content": f"Тема: {gs['selected_topic']}\nАнкор: {selected_anchor}",
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
            with st.expander("Предпросмотр статьи"):
                st.code(gs["article_html"][:800] + "...", language="html")

            if st.button("Сохранить в базу знаний", type="secondary"):
                save_project_example(
                    proj["id"],
                    gs["selected_topic"],
                    selected_anchor,
                    gs["article_html"],
                    "article_gen_prompt",
                )
                st.success("Сохранено!")

            # ШАГ 3: ПРОМПТЫ ДЛЯ КАРТИНОК (10 ШТУК)
            st.markdown("---")
            st.markdown("### Шаг 3: Промпты для изображений")

            if st.button("Сгенерировать 10 промптов", type="primary", key="gen_imgs"):
                with st.spinner("Генерация..."):
                    # Примеры хороших промптов
                    example_prompts = """
ПРИМЕРЫ ПРОМПТОВ:
1. Wide shot of industrial warehouse in Russia with steam generator units, Slavic workers in uniforms inspecting equipment, photorealistic, 16:9, no text
2. Close-up of professional Slavic engineer checking technical specifications on tablet next to industrial equipment, modern factory background, 8k, 16:9
3. Heavy-duty truck delivering steam generator unit on Russian highway, winter landscape, photorealistic, cinematic lighting, 16:9, no text
4. Team of Slavic technicians assembling industrial equipment in modern workshop, bright industrial lighting, professional workwear, 16:9, no text
5. Client meeting: Slavic businessman shaking hands with factory manager in front of ready-to-ship equipment, professional atmosphere, photorealistic, 16:9
"""
                    prompt = f"""Ты профессиональный промпт-инженер для Midjourney/DALL-E.

ТЕМА: {gs['selected_topic']}
КЛЮЧ: {selected_anchor}
НИША: {proj['niche']}

{example_prompts}

ЗАДАЧА: Создай 10 промптов для фотореалистичных изображений.

ТРЕБОВАНИЯ:
✅ Формат: 16:9, фотореализм, 8k
✅ Без текста на изображении
✅ Люди: только славянская внешность
✅ Контекст: {proj['niche']}
✅ Профессиональное освещение

ФОРМАТ:
1. [English prompt]
2. [English prompt]
...
10. [English prompt]"""

                    try:
                        resp = client.chat.completions.create(
                            model="llama-3.3-70b-versatile",
                            messages=[{"role": "user", "content": prompt}],
                            temperature=0.7,
                            max_tokens=1500,
                        )
                        gs["image_prompts"] = resp.choices[0].message.content.strip()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Ошибка: {str(e)[:100]}")

            if gs["image_prompts"]:
                st.code(gs["image_prompts"], language="text")

                st.download_button(
                    "Скачать все промпты",
                    data=gs["image_prompts"],
                    file_name=f"image_prompts_{datetime.now().strftime('%H%M')}.txt",
                    mime="text/plain",
                )

                # ШАГ 4: ФИНАЛЬНЫЙ ПРОМПТ
                st.markdown("---")
                st.markdown("### Шаг 4: Финальный экспорт")

                cols = st.columns(4)
                img_urls = [
                    st.text_input(
                        f"Img {i+1}",
                        value=f"https://i.postimg.cc/ex{i+1}.png",
                        key=f"im{i}",
                    )
                    for i in range(4)
                ]

                if st.button("Собрать финальный промпт", type="primary"):
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

                    if st.button("Сохранить в базу знаний", type="primary"):
                        save_project_example(
                            proj["id"],
                            gs["selected_topic"],
                            selected_anchor,
                            gs["article_html"],
                            gs["final_prompt"],
                        )
                        st.success("Сохранено!")

                    st.download_button(
                        "Скачать .txt",
                        data=gs["final_prompt"],
                        file_name=f"prompt_{datetime.now().strftime('%m%d_%H%M')}.txt",
                        mime="text/plain",
                    )
    render_footer()


# === РОУТИНГ ===
if st.session_state.view == "projects":
    render_project_selector()
elif st.session_state.view == "editor":
    render_project_editor()
elif st.session_state.view == "generator":
    render_generator()
