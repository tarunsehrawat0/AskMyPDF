import os
from pathlib import Path

import streamlit as st

from codex_runtime import PDFResearchAssistant, PDF_STORAGE_DIR


st.set_page_config(page_title='AskMyPDF', page_icon=':page_facing_up:', layout='wide')


def get_assistant() -> PDFResearchAssistant:
    if 'assistant' not in st.session_state:
        st.session_state.assistant = PDFResearchAssistant()
    return st.session_state.assistant


assistant = get_assistant()

if 'selected_documents' not in st.session_state:
    st.session_state.selected_documents = []

st.title('AskMyPDF')
st.caption('Upload PDFs, select one or more documents, and ask grounded questions.')

left_col, right_col = st.columns([1, 1], gap='large')

with left_col:
    st.subheader('Upload Documents')
    uploaded_files = st.file_uploader(
        'Upload one or more PDF files',
        type=['pdf'],
        accept_multiple_files=True,
        label_visibility='collapsed',
    )

    if st.button('Index Uploaded PDFs', use_container_width=True):
        if not uploaded_files:
            st.warning('Please upload at least one PDF first.')
        else:
            Path(PDF_STORAGE_DIR).mkdir(exist_ok=True)
            success_count = 0

            for uploaded_file in uploaded_files:
                pdf_path = os.path.join(PDF_STORAGE_DIR, uploaded_file.name)
                with open(pdf_path, 'wb') as out_file:
                    out_file.write(uploaded_file.getbuffer())

                result = assistant.add_pdf(uploaded_file.name, pdf_path)
                if result.get('success'):
                    success_count += 1

            if success_count:
                st.success(f'Indexed {success_count} file(s).')
            else:
                st.error('No files were indexed. Check the error logs and API key setup.')

    st.subheader('Indexed Documents')
    document_ids = list(assistant.documents.keys())

    if not document_ids:
        st.info('No documents indexed yet.')
    else:
        st.session_state.selected_documents = [
            doc_id for doc_id in st.session_state.selected_documents if doc_id in document_ids
        ]

        selected = st.multiselect(
            'Choose documents to search',
            options=document_ids,
            default=st.session_state.selected_documents,
            help='Leave empty to search across all indexed documents.',
        )
        st.session_state.selected_documents = selected

        st.dataframe(
            {
                'Document': [assistant.documents[doc_id]['name'] for doc_id in document_ids],
                'Chunks': [assistant.documents[doc_id]['chunk_count'] for doc_id in document_ids],
            },
            use_container_width=True,
            hide_index=True,
        )

    if st.button('Clear All Documents', type='secondary', use_container_width=True):
        assistant.documents = {}
        assistant.embeddings = []
        assistant.faiss_index = None
        assistant.save_metadata()
        st.session_state.selected_documents = []
        st.success('All indexed documents have been cleared.')

with right_col:
    st.subheader('Ask a Question')
    query = st.text_area('Enter your question', height=120, placeholder='What does the document say about...?')

    if st.button('Search and Answer', type='primary', use_container_width=True):
        if not query.strip():
            st.warning('Please enter a question.')
        else:
            with st.spinner('Generating answer...'):
                selected_docs = st.session_state.selected_documents or None
                result = assistant.ask(query.strip(), document_ids=selected_docs)

            st.subheader('Answer')
            st.markdown(result.get('answer', 'No answer generated.'))

            sources = result.get('sources', [])
            if sources:
                st.subheader('Sources')
                st.write(', '.join(sources))
