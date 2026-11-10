import base64
import html
import os
from pathlib import Path

import streamlit as st

from codex_runtime import PDFResearchAssistant, PDF_STORAGE_DIR


st.set_page_config(page_title='AskMyPDF', page_icon=':page_facing_up:', layout='wide')

st.markdown(
    """
    <style>
    :root {
        color-scheme: dark;
        --page: #101218;
        --panel: #181b23;
        --panel-raised: #222632;
        --border: #2b3040;
        --text: #f3f4f7;
        --muted: #a0a7b7;
        --accent: #f5a51c;
        --accent-soft: rgba(245, 165, 28, 0.12);
    }

    html, body, [data-testid="stAppViewContainer"], .stApp {
        background:
            radial-gradient(ellipse at 78% 5%, rgba(93, 71, 137, 0.12), transparent 34%),
            var(--page);
        color: var(--text);
    }
    [data-testid="stHeader"], [data-testid="stToolbar"], footer {
        display: none;
    }
    [data-testid="stMainBlockContainer"] {
        max-width: none;
        padding: 0 !important;
    }
    [data-testid="stHorizontalBlock"] {
        gap: 0 !important;
        align-items: stretch;
    }
    [data-testid="stVerticalBlock"] {
        gap: 0.65rem;
    }
    [data-testid="stMarkdownContainer"] p,
    [data-testid="stMarkdownContainer"] li {
        color: var(--text);
    }
    .st-key-sidebar_panel {
        height: calc(100dvh - 20px);
        min-height: 0;
        padding: 1.35rem 1.25rem;
        background:
            radial-gradient(ellipse at 5% 0%, rgba(245, 165, 28, 0.055), transparent 42%),
            var(--panel);
        border-right: 1px solid var(--border);
    }
    .st-key-chat_panel {
        height: 100%;
        min-height: 0;
        flex: 1 1 auto;
        padding: 1.35rem clamp(1rem, 4vw, 3.5rem) 1rem;
        display: flex;
        flex-direction: column;
    }
    @media (min-width: 761px) {
        [data-testid="stColumn"]:has(.st-key-chat_panel) > [data-testid="stVerticalBlock"] > [data-testid="stLayoutWrapper"] {
            flex: 1 1 0%;
            min-height: 0;
        }
    }
    .st-key-chat_panel > [data-testid="stLayoutWrapper"]:has(.st-key-chat_history) {
        display: flex;
        flex: 1 1 auto;
        min-height: 0;
    }
    .st-key-chat_history {
        flex: 1 1 auto;
        min-height: 0;
        overflow-y: auto;
        scrollbar-color: #3b4050 transparent;
        scrollbar-width: thin;
    }
    .st-key-chat_history:has(.empty-state) {
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .st-key-chat_history:has(.empty-state) > [data-testid="stLayoutWrapper"] {
        width: min(100%, 42rem);
    }
    .st-key-chat_panel > [data-testid="stLayoutWrapper"]:has(.st-key-composer) {
        margin-top: auto;
    }
    .brand {
        display: flex;
        align-items: center;
        gap: 0.72rem;
        margin: 0 0 1.5rem;
        color: var(--text);
        font-size: 1.55rem;
        font-weight: 780;
        letter-spacing: -0.04em;
    }
    .brand::before {
        content: "A";
        display: grid;
        width: 2.35rem;
        height: 2.35rem;
        place-items: center;
        border: 1px solid rgba(255, 198, 95, 0.32);
        border-radius: 0.8rem;
        background: linear-gradient(145deg, #ffc45c, #ee9410);
        box-shadow: 0 7px 20px rgba(245, 165, 28, 0.18);
        color: #251807;
        font-size: 1.2rem;
        font-weight: 900;
        letter-spacing: -0.06em;
    }
    .section-label {
        margin: 1.35rem 0 0.65rem;
        color: var(--muted);
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.11em;
        text-transform: uppercase;
    }
    .doc-row {
        margin: 0.45rem 0;
        padding: 0.8rem 0.85rem;
        overflow-wrap: anywhere;
        border: 1px solid #2b3040;
        border-radius: 0.8rem;
        background: linear-gradient(145deg, #232734, #1e222d);
        color: var(--text);
        font-size: 0.85rem;
        font-weight: 600;
        transition: border-color 160ms ease, transform 160ms ease;
    }
    .doc-row:hover {
        transform: translateY(-1px);
        border-color: #484e5e;
    }
    .doc-meta {
        margin-top: 0.3rem;
        color: var(--muted);
        font-size: 0.75rem;
        font-weight: 400;
    }
    .chat-topbar {
        display: flex;
        align-items: center;
        justify-content: flex-end;
        min-height: 2.8rem;
        margin-bottom: 0.6rem;
    }
    .doc-count {
        display: inline-flex;
        align-items: center;
        gap: 0.45rem;
        padding: 0.55rem 0.9rem;
        border: 1px solid #414756;
        border-radius: 0.8rem;
        background: rgba(29, 32, 41, 0.7);
        color: #e0e3ea;
        font-size: 0.85rem;
    }
    .doc-count::before {
        content: "";
        width: 0.45rem;
        height: 0.45rem;
        border-radius: 50%;
        background: #53d49b;
        box-shadow: 0 0 10px rgba(83, 212, 155, 0.55);
    }
    .empty-state {
        max-width: 35rem;
        margin: 0 auto;
        padding: clamp(1.4rem, 4vw, 2.5rem);
        border: 1px solid rgba(255, 255, 255, 0.075);
        border-radius: 1.5rem;
        background:
            radial-gradient(ellipse at 50% 0%, rgba(245, 165, 28, 0.1), transparent 60%),
            linear-gradient(145deg, rgba(31, 34, 44, 0.96), rgba(24, 27, 35, 0.96));
        box-shadow: 0 24px 70px rgba(0, 0, 0, 0.2);
        text-align: center;
    }
    .empty-icon {
        display: grid;
        width: 4rem;
        height: 4rem;
        margin: 0 auto 1.2rem;
        place-items: center;
        border: 1px solid rgba(255, 196, 92, 0.22);
        border-radius: 1.3rem;
        background: linear-gradient(145deg, rgba(245, 165, 28, 0.18), rgba(99, 78, 145, 0.2));
        color: #ffc45c;
        font-size: 1.7rem;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.18);
    }
    .empty-eyebrow {
        margin: 0 0 0.4rem;
        color: #ffc45c !important;
        font-size: 0.72rem;
        font-weight: 750;
        letter-spacing: 0.14em;
        text-transform: uppercase;
    }
    .empty-state h2 {
        margin: 0 0 0.6rem;
        color: var(--text);
        font-size: clamp(1.45rem, 3vw, 2rem);
        font-weight: 750;
        letter-spacing: -0.04em;
    }
    .empty-copy {
        max-width: 28rem;
        margin: 0 auto;
        color: var(--muted) !important;
        font-size: 0.95rem;
        line-height: 1.65;
    }
    .suggestion-list {
        display: flex;
        flex-wrap: wrap;
        justify-content: center;
        gap: 0.5rem;
        margin-top: 1.35rem;
    }
    .suggestion-list span {
        padding: 0.5rem 0.7rem;
        border: 1px solid #343949;
        border-radius: 999px;
        background: rgba(16, 18, 24, 0.55);
        color: #c6cbd6;
        font-size: 0.76rem;
    }
    [data-testid="stChatMessage"] {
        border: 0;
        background: transparent;
    }
    [data-testid="stChatMessageAvatarUser"],
    [data-testid="stChatMessageAvatarAssistant"] {
        position: relative;
        display: grid;
        width: 2.25rem;
        min-width: 2.25rem;
        height: 2.25rem;
        place-items: center;
        overflow: hidden;
        border: 1px solid rgba(255, 255, 255, 0.12);
        border-radius: 0.8rem;
        box-shadow: 0 5px 16px rgba(0, 0, 0, 0.24);
    }
    [data-testid="stChatMessageAvatarUser"] {
        background: linear-gradient(145deg, #5367d9, #8c52c7);
        color: #fff;
    }
    [data-testid="stChatMessageAvatarAssistant"] {
        background: linear-gradient(145deg, #ffc45c, #f3a018);
        color: #30200a;
    }
    [data-testid="stChatMessageAvatarUser"] > *,
    [data-testid="stChatMessageAvatarAssistant"] > * {
        visibility: hidden;
    }
    [data-testid="stChatMessageAvatarUser"]::after,
    [data-testid="stChatMessageAvatarAssistant"]::after {
        position: absolute;
        inset: 0;
        display: grid;
        place-items: center;
        font-family: ui-sans-serif, system-ui, sans-serif;
        font-size: 0.66rem;
        font-weight: 800;
        letter-spacing: 0.02em;
    }
    [data-testid="stChatMessageAvatarUser"]::after {
        content: "YOU";
    }
    [data-testid="stChatMessageAvatarAssistant"]::after {
        content: "AI";
        font-size: 0.75rem;
    }
    [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
        margin-left: auto;
        max-width: 78%;
        padding: 0.75rem 1rem;
        border-radius: 1.15rem 1.15rem 0.25rem 1.15rem;
        background: var(--accent);
        color: #17130c;
    }
    [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) p {
        color: #17130c;
    }
    [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) {
        max-width: 100%;
        margin: 0.35rem 0 0.8rem;
        padding: 1rem 1.1rem;
        border-radius: 1rem 1rem 1rem 0.25rem;
        background: #1d2029;
    }
    .source-chip {
        display: inline-block;
        margin: 0.55rem 0.35rem 0 0;
        padding: 0.4rem 0.7rem;
        border-radius: 999px;
        background: #2b3040;
        color: #ffc15b;
        font-size: 0.75rem;
    }
    .st-key-index_documents .stButton > button {
        box-shadow: 0 8px 22px rgba(245, 165, 28, 0.12);
    }
    .st-key-index_documents .stButton > button:hover,
    [data-testid="stFormSubmitButton"] > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 10px 25px rgba(245, 165, 28, 0.22);
        background: #ffb536;
    }
    .st-key-clear_documents .stButton > button {
        border: 1px solid rgba(247, 105, 105, 0.2);
        background: rgba(151, 54, 62, 0.12);
        color: #f09a9e !important;
    }
    .st-key-clear_documents .stButton > button p {
        color: #f09a9e !important;
    }
    .st-key-clear_documents .stButton > button:hover {
        border-color: rgba(247, 105, 105, 0.42);
        background: rgba(151, 54, 62, 0.22);
    }
    .st-key-composer {
        position: sticky;
        bottom: 0;
        z-index: 5;
        padding-top: 0.75rem;
        background: linear-gradient(180deg, transparent, var(--page) 18%);
    }
    [data-testid="stForm"] {
        padding: 0.45rem 0.55rem 0.45rem 0.9rem;
        border: 1px solid #343a49;
        border-radius: 1rem;
        background: #1c1f28;
    }
    [data-testid="stForm"] [data-testid="stTextInput"] input {
        border: 0;
        background: transparent;
        box-shadow: none;
    }
    [data-testid="stForm"] [data-testid="stTextInput"] input:focus {
        border: 0;
        box-shadow: none;
    }
    [data-testid="stCheckbox"] label > div:nth-of-type(1) {
        border-color: #555c6d;
        background: #222632;
    }
    [data-testid="stCheckbox"] label[data-selected="true"] > div:nth-of-type(1) {
        border-color: var(--accent);
        background: var(--accent);
        color: #201605;
    }
    [data-testid="stCheckbox"] label:focus-within > div:nth-of-type(1) {
        outline: 2px solid rgba(245, 165, 28, 0.35);
        outline-offset: 2px;
    }
    [data-testid="stFileUploader"] button {
        border: 1px solid #3a4050;
        border-radius: 0.7rem;
        background: #232734;
        color: var(--text);
    }
    [data-testid="stFileUploader"] button:hover {
        border-color: #666d7e;
        color: #fff;
    }
    .stButton > button,
    [data-testid="stFormSubmitButton"] > button {
        min-height: 2.7rem;
        border: 0;
        border-radius: 0.8rem;
        background: var(--accent);
        color: #17130c !important;
        font-weight: 700;
    }
    .stButton > button p,
    [data-testid="stFormSubmitButton"] > button p {
        color: #17130c !important;
    }
    [data-testid="stFileUploader"] section {
        border: 1px dashed #414756;
        border-radius: 0.9rem;
        background: transparent;
    }
    [data-testid="stCheckbox"] label,
    [data-testid="stExpander"] summary {
        color: var(--text);
    }
    [data-testid="stCheckbox"] input {
        accent-color: var(--accent);
    }
    [data-testid="stExpander"] {
        border-color: var(--border);
        background: #1d2029;
    }

    @media (max-width: 760px) {
        [data-testid="stHorizontalBlock"]:has(.st-key-sidebar_panel),
        [data-testid="stHorizontalBlock"]:has(.st-key-chat_panel) {
            flex-direction: column;
        }
        .st-key-sidebar_panel {
            height: auto;
            min-height: 0;
            padding: 1rem;
            border-right: 0;
            border-bottom: 1px solid var(--border);
        }
        .st-key-chat_panel {
            height: min(72dvh, 760px);
            min-height: 500px;
            padding: 0.8rem 1rem 1rem;
        }
        .brand {
            margin-bottom: 0.8rem;
            font-size: 1.3rem;
        }
        .brand::before {
            width: 2rem;
            height: 2rem;
            border-radius: 0.7rem;
        }
        .section-label {
            margin-top: 0.85rem;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def get_assistant() -> PDFResearchAssistant:
    if 'assistant' not in st.session_state:
        st.session_state.assistant = PDFResearchAssistant()
    return st.session_state.assistant


assistant = get_assistant()
document_ids = list(assistant.documents.keys())

if 'selected_documents' not in st.session_state:
    st.session_state.selected_documents = document_ids.copy()
if 'messages' not in st.session_state:
    st.session_state.messages = []

st.session_state.selected_documents = [
    doc_id for doc_id in st.session_state.selected_documents if doc_id in document_ids
]

sidebar, chat = st.columns([0.36, 0.64], gap='small')

with sidebar:
    with st.container(key='sidebar_panel'):
        st.markdown('<h1 class="brand">AskMyPDF</h1>', unsafe_allow_html=True)
        st.markdown('<div class="section-label">Add PDFs</div>', unsafe_allow_html=True)
        uploaded_files = st.file_uploader(
            'Add PDF documents',
            type=['pdf'],
            accept_multiple_files=True,
            label_visibility='collapsed',
        )
        analyze_images = st.checkbox(
            'Analyze images',
            value=True,
            help='Extract and analyze PDF images using the OpenAI API.',
        )

        if st.button('Index uploaded PDFs', key='index_documents', use_container_width=True):
            if not uploaded_files:
                st.warning('Choose at least one PDF before indexing.')
            else:
                Path(PDF_STORAGE_DIR).mkdir(parents=True, exist_ok=True)
                success_count = 0
                with st.spinner('Indexing PDFs...'):
                    for uploaded_file in uploaded_files:
                        filename = Path(uploaded_file.name).name
                        pdf_path = os.path.join(PDF_STORAGE_DIR, filename)
                        with open(pdf_path, 'wb') as out_file:
                            out_file.write(uploaded_file.getbuffer())

                        result = assistant.add_pdf(
                            filename,
                            pdf_path,
                            analyze_images=analyze_images,
                        )
                        if result.get('success'):
                            success_count += 1

                if success_count:
                    st.session_state.selected_documents = list(assistant.documents.keys())
                    st.success(f'Indexed {success_count} PDF(s).')
                    st.rerun()
                else:
                    st.error('No PDFs were indexed. Check the application logs.')

        st.markdown('<div class="section-label">Documents</div>', unsafe_allow_html=True)
        document_ids = list(assistant.documents.keys())
        selected_documents = []
        if document_ids:
            for doc_id in document_ids:
                doc = assistant.documents[doc_id]
                name = html.escape(doc.get('name', doc_id))
                chunks = len(doc.get('chunks', []))
                image_count = doc.get('image_count', 0)
                check_col, info_col = st.columns([0.1, 0.9], gap='small')
                with check_col:
                    is_selected = st.checkbox(
                        f'Use {doc.get("name", doc_id)}',
                        value=doc_id in st.session_state.selected_documents,
                        key=f'document_{doc_id}',
                        label_visibility='collapsed',
                    )
                with info_col:
                    st.markdown(
                        f'<div class="doc-row">{name}'
                        f'<div class="doc-meta">{chunks} chunks · {image_count} images</div></div>',
                        unsafe_allow_html=True,
                    )
                if is_selected:
                    selected_documents.append(doc_id)
            st.session_state.selected_documents = selected_documents
        else:
            st.caption('Your uploaded PDFs will appear here.')

        selected_with_images = [
            doc_id for doc_id in st.session_state.selected_documents
            if assistant.documents.get(doc_id, {}).get('images')
        ]
        if selected_with_images:
            with st.expander('View extracted images'):
                for doc_id in selected_with_images:
                    doc = assistant.documents[doc_id]
                    st.markdown(f'**{doc["name"]}**')
                    for image in doc.get('images', [])[:10]:
                        st.image(
                            base64.b64decode(image['base64']),
                            caption=f'Page {image.get("page", "?")}',
                            width=180,
                        )
                        if image.get('description'):
                            st.caption(image['description'])

        if st.button('Clear all documents', key='clear_documents', use_container_width=True):
            assistant.documents = {}
            assistant.embeddings = []
            assistant.faiss_index = None
            assistant.save_metadata()
            st.session_state.selected_documents = []
            st.session_state.messages = []
            st.rerun()

with chat:
    with st.container(key='chat_panel'):
        count = len(assistant.documents)
        st.markdown(
            f'<div class="chat-topbar"><span class="doc-count">Docs ({count})</span></div>',
            unsafe_allow_html=True,
        )

        with st.container(key='chat_history'):
            if not st.session_state.messages:
                selected_count = len(st.session_state.selected_documents)
                document_label = 'document' if selected_count == 1 else 'documents'
                st.markdown(
                    f'<section class="empty-state">'
                    f'<div class="empty-icon" aria-hidden="true">✦</div>'
                    f'<p class="empty-eyebrow">Your PDF research space</p>'
                    f'<h2>Your documents, ready to talk.</h2>'
                    f'<p class="empty-copy">Ask a question and get a clear answer grounded in your PDFs, '
                    f'with sources included. {selected_count} {document_label} selected.</p>'
                    f'<div class="suggestion-list">'
                    f'<span>Summarize key ideas</span>'
                    f'<span>Explain a topic</span>'
                    f'<span>Find important details</span>'
                    f'</div></section>',
                    unsafe_allow_html=True,
                )
            else:
                for message in st.session_state.messages:
                    with st.chat_message(message['role']):
                        st.markdown(message['content'])
                        if message.get('sources'):
                            chips = ''.join(
                                '<span class="source-chip">'
                                f'Source {index} · {html.escape(source)}'
                                '</span>'
                                for index, source in enumerate(message['sources'], start=1)
                            )
                            st.markdown(chips, unsafe_allow_html=True)

        with st.container(key='composer'):
            with st.form('question_form', clear_on_submit=True):
                prompt_col, send_col = st.columns([0.85, 0.15], gap='small')
                with prompt_col:
                    query = st.text_input(
                        'Question',
                        placeholder='Ask about your PDFs...',
                        label_visibility='collapsed',
                    )
                with send_col:
                    submitted = st.form_submit_button('Send', use_container_width=True)

            if submitted:
                if not query.strip():
                    st.warning('Enter a question to continue.')
                elif not st.session_state.selected_documents:
                    st.warning('Select at least one document in the sidebar.')
                else:
                    with st.spinner('Finding an answer in your PDFs...'):
                        result = assistant.ask(
                            query.strip(),
                            document_ids=st.session_state.selected_documents,
                        )
                    st.session_state.messages.extend(
                        [
                            {'role': 'user', 'content': query.strip()},
                            {
                                'role': 'assistant',
                                'content': result.get('answer', 'No answer was generated.'),
                                'sources': result.get('sources', []),
                            },
                        ]
                    )
                    st.rerun()
