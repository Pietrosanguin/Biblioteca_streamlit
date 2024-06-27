import streamlit as st
import pandas as pd
from PIL import Image
import io
import pickle
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import streamlit_authenticator as stauth
from datetime import datetime
from googleapiclient.http import MediaIoBaseDownload
import re

# -- USER AUTHENTICATION --

names = ["Claudio"]
usernames = ["Claudio"]

# Load hashed passwords
file_path = "hashed_pw.pkl"
with open(file_path, "rb") as file:
    hashed_passwords = pickle.load(file)

authenticator = stauth.Authenticate(names, usernames, hashed_passwords,
    "biblioteca_domestica", "abcdef", cookie_expiry_days=0)

name, authentication_status, username = authenticator.login("Login", "main")

if authentication_status == False:
    st.error("Username/password is incorrect")

if authentication_status == None:
    st.warning("Please enter your username and password")

if authentication_status:
    # Function to upload image to Google Drive
    def upload_image_to_drive(cover, drive_service, folder_id):
        try:
            file_metadata = {
                'name': cover.name,
                'mimeType': cover.type,
                'parents': [folder_id]
            }
            media = MediaIoBaseUpload(io.BytesIO(st.session_state['cover_image']), mimetype=cover.type)
            uploaded_file = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
            file_id = uploaded_file.get('id')
            file_url = f'https://drive.google.com/uc?id={file_id}'
            return file_url
        except Exception as error:
            st.error(f'An error occurred: {error}')
            return None
    
    def extract_file_id(file_url):
        # Regular expression to extract file ID from the URL
        match = re.search(r'id=([a-zA-Z0-9-_]+)', file_url)
        if match:
            return match.group(1)
        else:
            raise ValueError("Invalid file URL")
        
    def get_image_from_drive(drive_service, file_id):
        file_id = extract_file_id(file_id)
        request = drive_service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
        fh.seek(0)
        return fh

    # Function to append data to Google Sheets
    def append_to_sheets(sheets_service, sheet_id, data, range_name='Foglio1'):
        value_input_option = 'RAW'
        value_range_body = {'values': [data]}
        sheets_service.spreadsheets().values().append(
            spreadsheetId=sheet_id,
            range=range_name,
            valueInputOption=value_input_option,
            insertDataOption='INSERT_ROWS',
            body=value_range_body
        ).execute()

    # Function to get all books from Google Sheets
    def get_all_books(sheets_service, sheet_id, columns_range='B:H'):
        result = sheets_service.spreadsheets().values().get(spreadsheetId=sheet_id, range=f'Foglio1!{columns_range}').execute()
        return result.get('values', [])
    

    def update_book(sheets_service, sheet_id, book_ts_id, data):
        # Step 1: Retrieve the data from the sheet
        range_name = 'Foglio1!A:H'  # Adjust the range as needed
        result = sheets_service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range=range_name
        ).execute()
        values = result.get('values', [])

        # Step 2: Iterate through the rows and check for the condition in column A
        for i, row in enumerate(values):
            if len(row) > 0 and row[0] == book_ts_id:
                # Step 3: Update the row with the new data
                range_name = f'Foglio1!B{i+1}:H{i+1}'
                value_input_option = 'RAW'
                value_range_body = {'values': [data]}
                sheets_service.spreadsheets().values().update(
                    spreadsheetId=sheet_id,
                    range=range_name,
                    valueInputOption=value_input_option,
                    body=value_range_body
                ).execute()
                break

    # Function to delete a book from Google Sheets
    def delete_book(sheets_service, sheet_id, book_ts_id):

        range_name = 'Foglio1!A:H'  # Adjust the range as needed
        result = sheets_service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range=range_name
        ).execute()
        values = result.get('values', [])

        for i, row in enumerate(values):
            if len(row) > 0 and row[0] == book_ts_id:
                # Delete the row data
                requests = [{
                    'deleteRange': {
                        'range': {
                            'sheetId': 0,
                            'startRowIndex': i,
                            'endRowIndex': i + 1,
                        },
                        'shiftDimension': 'ROWS'
                    }
                }]
                body = {'requests': requests}
                sheets_service.spreadsheets().batchUpdate(spreadsheetId=sheet_id, body=body).execute()

    # Function to paginate DataFrame
    def paginate(df, page_size, page_num):
        return df.iloc[page_num*page_size:(page_num+1)*page_size]


    # Main function for the Streamlit app
    def main():
        st.title('Gestione della Biblioteca Domestica')

        st.sidebar.title(f"Benvenuto {name}")
        menu = ['Inserisci Nuovo Libro', 'Ricerca e Modifica Libri']
        choice = st.sidebar.selectbox('Menu', menu)

        if choice == 'Inserisci Nuovo Libro':
            st.subheader('Inserisci Nuovo Libro')

            if 'cover_image' not in st.session_state:
                st.session_state['cover_image'] = None

            with st.form(key='insert_form'):
                title = st.text_input('Titolo')
                author = st.text_input('Autore')
                genre = st.text_input('Genere')

                col1, col2, col3 = st.columns(3)
                with col1:
                    publisher = st.text_input('Casa Editrice')
                with col2:
                    city = st.text_input('Città')
                with col3:
                    year = st.text_input('Anno')

                shelf = st.text_input('Scaffale')
                cover = st.file_uploader('Carica Copertina', type=['jpg', 'png', 'jpeg'])

                if cover:
                    st.session_state['cover_image'] = cover.read()
                    image = Image.open(io.BytesIO(st.session_state['cover_image']))
                    resized_image = image.resize((250, 250))  # Resize image to 250x250 pixels
                    st.image(resized_image)
                elif st.session_state['cover_image']:
                    image = Image.open(io.BytesIO(st.session_state['cover_image']))
                    resized_image = image.resize((250, 250))  # Resize image to 250x250 pixels
                    st.image(resized_image)

                submit_button = st.form_submit_button(label='Aggiungi Libro')

                if submit_button:
                    if not title:
                        st.error('Campo "Titolo" vuoto. Se non disponibile, scrivere None')
                    elif not author:
                        st.error('Campo "Autore" vuoto. Se non disponibile, scrivere None')
                    elif not genre:
                        st.error('Campo "Genere" vuoto. Se non disponibile, scrivere None')
                    elif not publisher:
                        st.error('Campo "Casa Editrice" vuoto. Se non disponibile, scrivere None')
                    elif not city:
                        st.error('Campo "Città" vuoto. Se non disponibile, scrivere None')
                    elif not year:
                        st.error('Campo "Anno" vuoto. Se non disponibile, scrivere None')
                    elif not shelf:
                        st.error('Campo "Scaffale" vuoto. Se non disponibile, scrivere None')
                    else:
                        credentials_info = {
                            "type": st.secrets["gcp_service_account"]["type"],
                            "project_id": st.secrets["gcp_service_account"]["project_id"],
                            "private_key_id": st.secrets["gcp_service_account"]["private_key_id"],
                            "private_key": st.secrets["gcp_service_account"]["private_key"],
                            "client_email": st.secrets["gcp_service_account"]["client_email"],
                            "client_id": st.secrets["gcp_service_account"]["client_id"],
                            "auth_uri": st.secrets["gcp_service_account"]["auth_uri"],
                            "token_uri": st.secrets["gcp_service_account"]["token_uri"],
                            "auth_provider_x509_cert_url": st.secrets["gcp_service_account"]["auth_provider_x509_cert_url"],
                            "client_x509_cert_url": st.secrets["gcp_service_account"]["client_x509_cert_url"]
                        }

                        credentials = service_account.Credentials.from_service_account_info(
                            credentials_info,
                            scopes=['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/spreadsheets']
                        )

                        drive_service = build('drive', 'v3', credentials=credentials)
                        sheets_service = build('sheets', 'v4', credentials=credentials)

                        folder_id = '1om43VabKHa0KnW5aTm6tAN8sqZGHfoLV' 
                        file_url = upload_image_to_drive(cover, drive_service, folder_id)

                        if file_url:
                            sheet_id = '1zkUbM0XUGH9WZ8FlxdGGgianA2tSpeQQJagzlBFQidY'
                            data = [str(datetime.now()), title, author, genre, publisher, city, year, shelf, file_url]
                            append_to_sheets(sheets_service, sheet_id, data)
                            st.success(f'Libro "{title}" aggiunto con successo!')
                            st.session_state['cover_image'] = None
                        else:
                            st.error('File upload failed.')

        elif choice == 'Ricerca e Modifica Libri':

            credentials_info = {
                "type": st.secrets["gcp_service_account"]["type"],
                "project_id": st.secrets["gcp_service_account"]["project_id"],
                "private_key_id": st.secrets["gcp_service_account"]["private_key_id"],
                "private_key": st.secrets["gcp_service_account"]["private_key"],
                "client_email": st.secrets["gcp_service_account"]["client_email"],
                "client_id": st.secrets["gcp_service_account"]["client_id"],
                "auth_uri": st.secrets["gcp_service_account"]["auth_uri"],
                "token_uri": st.secrets["gcp_service_account"]["token_uri"],
                "auth_provider_x509_cert_url": st.secrets["gcp_service_account"]["auth_provider_x509_cert_url"],
                "client_x509_cert_url": st.secrets["gcp_service_account"]["client_x509_cert_url"]
            }

            credentials = service_account.Credentials.from_service_account_info(
                credentials_info,
                scopes=['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/spreadsheets']
            )

            drive_service = build('drive', 'v3', credentials=credentials)
            sheets_service = build('sheets', 'v4', credentials=credentials)

            folder_id = '1om43VabKHa0KnW5aTm6tAN8sqZGHfoLV'

            st.subheader('Ricerca e Modifica Libri')

            search_term = st.text_input('Cerca per Titolo o Autore')
            genre_filter = st.text_input('Filtra per Genere')
            search_button = st.button('Cerca')

            if 'page_num' not in st.session_state:
                st.session_state['page_num'] = 0

            if search_button:
                st.session_state['page_num'] = 0  # Reset to the first page on new search



            books = get_all_books(sheets_service, '1zkUbM0XUGH9WZ8FlxdGGgianA2tSpeQQJagzlBFQidY', columns_range='A:I')
            df = pd.DataFrame(books[1:], columns=['ts', 'Titolo', 'Autore', 'Genere', 'Casa Editrice', 'Città', 'Anno', 'Scaffale', 'Copertina'])

            if search_term:
                df = df[df.apply(lambda row: search_term.lower() in row['Titolo'].lower() or search_term.lower() in row['Autore'].lower(), axis=1)]
            if genre_filter:
                df = df[df['Genere'].str.contains(genre_filter, case=False)]

            page_size = 10
            max_page_num = (len(df) // page_size)
            paginated_df = paginate(df, page_size, st.session_state['page_num'])

            st.dataframe(paginated_df[['Titolo', 'Autore', 'Genere', 'Casa Editrice', 'Città', 'Anno', 'Scaffale']])

            col1, col2, col3 = st.columns([1, 1, 1])
            with col1:
                if st.button('Precedente') and st.session_state['page_num'] > 0:
                    st.session_state['page_num'] -= 1
            with col2:
                st.write(f'Pagina {st.session_state["page_num"] + 1} di {max_page_num + 1}')
            with col3:
                if st.button('Successivo') and st.session_state['page_num'] < max_page_num:
                    st.session_state['page_num'] += 1

            for i, row in paginated_df.iterrows():
                if st.session_state.get(f"edit_mode_{row['ts']}"):
                    st.markdown(f"### Modifica libro: {row['Titolo']}")
                    new_title = st.text_input('Titolo', value=row['Titolo'], key=f"title_{row['ts']}")
                    new_author = st.text_input('Autore', value=row['Autore'], key=f"author_{row['ts']}")
                    new_genre = st.text_input('Genere', value=row['Genere'], key=f"genre_{row['ts']}")

                    col1, col2, col3 = st.columns(3)
                    with col1:
                        new_publisher = st.text_input('Casa Editrice', value=row['Casa Editrice'], key=f"publisher_{row['ts']}")
                    with col2:
                        new_city = st.text_input('Città', value=row['Città'], key=f"city_{row['ts']}")
                    with col3:
                        new_year = st.text_input('Anno', value=row['Anno'], key=f"year_{row['ts']}")

                    new_shelf = st.text_input('Scaffale', value=row['Scaffale'], key=f"shelf_{row['ts']}")
                    if st.button(f'Aggiorna "{row["Titolo"]}"', key=f"update_{row['ts']}"):
                        update_book(sheets_service, '1zkUbM0XUGH9WZ8FlxdGGgianA2tSpeQQJagzlBFQidY', row['ts'], [new_title, new_author, new_genre, new_publisher, new_city, new_year, new_shelf])
                        st.success(f'Libro "{new_title}" aggiornato con successo!')
                        st.session_state[f"edit_mode_{row['ts']}"] = False
                        st.rerun()  # Rerun the app to refresh the data
                else:
                    st.markdown(f"### Titolo: **{row['Titolo']}**")
                    st.markdown(f"**Autore:** {row['Autore']}")
                    st.markdown(f"**Genere:** {row['Genere']}")
                    st.markdown(f"**Casa Editrice:** {row['Casa Editrice']}")
                    st.markdown(f"**Città:** {row['Città']}")
                    st.markdown(f"**Anno:** {row['Anno']}")
                    st.markdown(f"**Scaffale:** {row['Scaffale']}")
                    if row['Copertina']:
                        image = get_image_from_drive(drive_service, row['Copertina'])
                        st.image(image, caption=row['Titolo'], width=300)


                    if st.button(f"Modifica '{row['Titolo']}'", key=f"mod_{row['ts']}"):
                        st.session_state[f"edit_mode_{row['ts']}"] = True

                if st.button(f"Elimina '{row['Titolo']}'", key=f"del_{row['ts']}"):
                    st.session_state[f"delete_mode_{row['ts']}"] = True

                if st.session_state.get(f"delete_mode_{row['ts']}"):
                    confirm_delete = st.checkbox(f'Conferma eliminazione del libro "{row["Titolo"]}"', key=f'confirm_del_{row["ts"]}')
                    if confirm_delete:
                        delete_book(sheets_service, '1zkUbM0XUGH9WZ8FlxdGGgianA2tSpeQQJagzlBFQidY', row['ts'])
                        st.success(f'Libro "{row["Titolo"]}" eliminato con successo!')
                        st.session_state[f"delete_mode_{row['ts']}"] = False
                        st.rerun()  # Rerun the app to refresh the data

    if __name__ == '__main__':
        main()
