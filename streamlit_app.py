import os
import base64
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

    analyze_images = st.checkbox('Analyze images in PDFs (requires OpenAI API)', value=True, help='Extract and analyze images using GPT-4 Vision for better search results')
    
    if st.button('Index Uploaded PDFs', use_container_width=True):
        if not uploaded_files:
            st.warning('Please upload at least one PDF first.')
        else:
            Path(PDF_STORAGE_DIR).mkdir(exist_ok=True)
            success_count = 0
            total_images = 0
            
            with st.spinner('Indexing PDFs... This may take a few minutes if images are being analyzed.'):
                for uploaded_file in uploaded_files:
                    pdf_path = os.path.join(PDF_STORAGE_DIR, uploaded_file.name)
                    with open(pdf_path, 'wb') as out_file:
                        out_file.write(uploaded_file.getbuffer())

                    result = assistant.add_pdf(uploaded_file.name, pdf_path, analyze_images=analyze_images)
                    if result.get('success'):
                        success_count += 1
                        total_images += result.get('image_count', 0)

            if success_count:
                msg = f'Indexed {success_count} file(s).'
                if total_images > 0:
                    msg += f' Found and analyzed {total_images} image(s).'
                st.success(msg)
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
                'Images': [assistant.documents[doc_id].get('image_count', 0) for doc_id in document_ids],
            },
            use_container_width=True,
            hide_index=True,
        )
        
        # Show images for selected documents
        if selected:
            st.subheader('Extracted Images')
            for doc_id in selected:
                if doc_id in assistant.documents and assistant.documents[doc_id].get('images'):
                    images = assistant.documents[doc_id]['images']
                    st.write(f"**{assistant.documents[doc_id]['name']}** ({len(images)} images)")
                    
                    for img in images[:10]:  # Show first 10 images to avoid overwhelming
                        col1, col2 = st.columns([1, 3])
                        with col1:
                            # Display image from base64
                            image_data = base64.b64decode(img['base64'])
                            st.image(image_data, caption=f"Page {img['page']}", use_column_width=True)
                        with col2:
                            if img.get('description'):
                                st.info(f"**Description:** {img['description']}")
                        st.divider()
                    
                    if len(images) > 10:
                        st.caption(f"... and {len(images) - 10} more images")

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
