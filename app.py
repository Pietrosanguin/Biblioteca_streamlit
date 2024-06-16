import streamlit as st
import pandas as pd
import sqlite3
from PIL import Image
import io
import pickle
from pathlib import Path

import streamlit_authenticator as stauth

from utils import *

# -- USER AUTHENTICATION --

names = ["Claudio", "Pietro"]
usernames = ["Claudio", "Pietro"]

# load hashed passwords
file_path = "hashed_pw.pkl"
with open(file_path, "rb") as file:
    hashed_passwords = pickle.load(file)

authenticator = stauth.Authenticate(names, usernames, hashed_passwords,
    "biblioteca_domestica", "abcdef", cookie_expiry_days=30)

name, authentication_status, username = authenticator.login("Login", "main")


if authentication_status == False:
    st.error("Username/password is incorrect")

if authentication_status == None:
    st.warning("Please enter your username and password")

if authentication_status:

    # Main function for the Streamlit app
    def main():
        st.title('Gestione della Biblioteca Domestica')

        #authenticator.logout(button_name="Logout", location="sidebar")
        st.sidebar.title(f"Benvenuto {name}")
        menu = ['Inserisci Nuovo Libro', 'Ricerca e Modifica Libri']
        choice = st.sidebar.selectbox('Menu', menu)

        create_table()

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
                    cover_image = st.session_state['cover_image']
                    add_book(title, author, genre, publisher, city, year, cover_image, shelf)
                    st.success(f'Libro "{title}" aggiunto con successo!')
                    st.session_state['cover_image'] = None

        elif choice == 'Ricerca e Modifica Libri':
            st.subheader('Ricerca e Modifica Libri')
            
            search_term = st.text_input('Cerca per Titolo o Autore')
            genre_filter = st.text_input('Filtra per Genere')
            search_button = st.button('Cerca')

            if 'page_num' not in st.session_state:
                st.session_state['page_num'] = 0
            
            if search_button:
                st.session_state['page_num'] = 0  # Reset to the first page on new search

            books = get_all_books()
            df = pd.DataFrame(books, columns=['ID', 'Titolo', 'Autore', 'Genere', 'Casa Editrice', 'Città', 'Anno', 'Copertina', 'Scaffale'])

            # Perform case-insensitive search and filtering
            if search_term:
                df = df[df.apply(lambda row: search_term.lower() in row['Titolo'].lower() or search_term.lower() in row['Autore'].lower(), axis=1)]
            if genre_filter:
                df = df[df['Genere'].str.contains(genre_filter, case=False)]

            page_size = 10
            max_page_num = (len(df) // page_size)

            
            paginated_df = paginate(df, page_size, st.session_state['page_num'])

            st.dataframe(paginated_df[['Titolo', 'Autore', 'Genere', 'Casa Editrice', 'Città', 'Anno', 'Scaffale']])

            # Pagination buttons
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
                if st.session_state.get(f"edit_mode_{row['ID']}"):
                    st.markdown(f"### Modifica libro: {row['Titolo']}")
                    new_title = st.text_input('Titolo', value=row['Titolo'], key=f"title_{row['ID']}")
                    new_author = st.text_input('Autore', value=row['Autore'], key=f"author_{row['ID']}")
                    new_genre = st.text_input('Genere', value=row['Genere'], key=f"genre_{row['ID']}")

                    col1, col2, col3 = st.columns(3)
                    with col1:
                        new_publisher = st.text_input('Casa Editrice', value=row['Casa Editrice'], key=f"publisher_{row['ID']}")
                    with col2:
                        new_city = st.text_input('Città', value=row['Città'], key=f"city_{row['ID']}")
                    with col3:
                        new_year = st.text_input('Anno', value=row['Anno'], key=f"year_{row['ID']}")

                    new_shelf = st.text_input('Scaffale', value=row['Scaffale'], key=f"shelf_{row['ID']}")
                    if st.button(f'Aggiorna "{row["Titolo"]}"', key=f"update_{row['ID']}"):
                        update_book(row['ID'], new_title, new_author, new_genre, new_publisher, new_city, new_year, new_shelf)
                        st.success(f'Libro "{new_title}" aggiornato con successo!')
                        st.session_state[f"edit_mode_{row['ID']}"] = False
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
                        image = Image.open(io.BytesIO(row['Copertina']))
                        st.image(image, caption=row['Titolo'], width=300)  # Set the width to 300

                    if st.button(f"Modifica '{row['Titolo']}'", key=f"mod_{row['ID']}"):
                        st.session_state[f"edit_mode_{row['ID']}"] = True

                if st.button(f"Elimina '{row['Titolo']}'", key=f"del_{row['ID']}"):
                    st.session_state[f"delete_mode_{row['ID']}"] = True

                if st.session_state.get(f"delete_mode_{row['ID']}"):
                    confirm_delete = st.checkbox(f'Conferma eliminazione del libro "{row["Titolo"]}"', key=f'confirm_del_{row["ID"]}')
                    if confirm_delete:
                        delete_book(row['ID'])
                        st.success(f'Libro "{row["Titolo"]}" eliminato con successo!')
                        st.session_state[f"delete_mode_{row['ID']}"] = False
                        st.rerun()  # Rerun the app to refresh the data


    if __name__ == '__main__':
        main()
