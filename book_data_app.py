import psycopg2
import requests
import PySimpleGUI as sg


db_connection = None
db_cursor = None

def fetch_book_data(isbn):
    base_url = "https://data.bn.org.pl/api/bibs.json"
    params = {"isbnIssn": isbn}

    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        data = response.json()

        book_data = data.get("bibs", [])
        if book_data:
            book_data = book_data[0]
            isbn = book_data.get("isbnIssn")
            return {
                "isbn": isbn,
                "title": book_data.get("title"),
                "author": book_data.get("author"),
                "publisher": book_data.get("publisher"),
                "language": book_data.get("language")
            }
        else:
            sg.popup("Brak danych dla podanego numeru ISBN.")
            return None

    except requests.exceptions.RequestException as e:
        print("Wystapil blad podczas pobierania danych z API:", e)
        return None

def is_book_in_database(isbn):
    try:
        cursor = db_connection.cursor()

        query = "SELECT * FROM Books WHERE isbn = %s"
        cursor.execute(query, (isbn,))
        book = cursor.fetchone()

        return book is not None
    except Exception as e:
        print("Wystapil blad podczas sprawdzania ksiazki w bazie danych:", e)
        return False

def save_book_to_database(book_data):
    try:
        cursor = db_connection.cursor()

        query = "INSERT INTO Books (isbn, title, author, publisher, language) VALUES (%s, %s, %s, %s, %s)"
        values = (book_data.get("isbn"), book_data.get("title"), book_data.get("author"), book_data.get("publisher"), book_data.get("language"))
        
        cursor.execute(query, values)
        db_connection.commit()
        print("Dane ksiazki zostaly zapisane do bazy danych.")
    except Exception as e:
        print("Wystapil blad podczas zapisywania danych do bazy danych:", e)

def get_books_from_database():
    try:
        cursor = db_connection.cursor()

        query = "SELECT id, isbn, title, author, publisher, language FROM Books"
        cursor.execute(query)
        books = cursor.fetchall()

        return books
    except Exception as e:
        print("Wystapil blad podczas pobierania danych z bazy danych:", e)
        return []
        
def delete_book_from_database(book_id):
    try:
        cursor = db_connection.cursor()

        query = "DELETE FROM Books WHERE id = %s"
        cursor.execute(query, (book_id,))
        db_connection.commit()
        sg.popup("Ksiazka zostala usunieta z bazy danych.", font=("Helvetica", 14))
    except Exception as e:
        print("Wystapil blad podczas usuwania ksiazki z bazy danych:", e)
        
def main():
    global db_connection
    global db_cursor
    sg.theme("DefaultNoMoreNagging")

    try:
        db_connection = psycopg2.connect(
            host="localhost",
            user="postgres",
            password="btE62Ay#9E",
            database="hubert"
        )
        db_cursor = db_connection.cursor()

        initial_books = get_books_from_database()
        
        # Definiowanie minimalnych szerokosci kolumn
        min_col_widths = [30, 500, 150, 100, 100, 100, 100]

        layout = [
            [sg.Text("Podaj numer ISBN:", font=("Helvetica", 14))],
            [sg.Input(key="-ISBN-")],
            [sg.Button(image_filename="search.png", key="-SEARCH", image_size=(30, 30)), 
            sg.Button(image_filename="delete.png", key="-DELETE_SELECTED", image_size=(30, 30)), 
            sg.Button(image_filename="refresh.png", key="-REFRESH", image_size=(30, 30)), 
            sg.Button(image_filename="exit.png", key="-EXIT", image_size=(30, 30))],
            [sg.Text("Twoje ksiazki:", font=("Helvetica", 14))],
            [sg.Table(values=initial_books,
                       headings=["ID", "ISBN", "Tytul", "Autor", "Wydawca", "Jezyk"],
                       auto_size_columns=True,
                       display_row_numbers=False,
                       num_rows=30,
                       col_widths=min_col_widths,
                       key="-BOOKS-")]
        ]

        window = sg.Window("Ksiazki API", layout, resizable=True)

        while True:
            event, values = window.read()

            if event == sg.WIN_CLOSED or event == "-EXIT":
                break
                
            if event == "-DELETE_SELECTED":
                selected_rows = values["-BOOKS-"]  # Zaznaczone wiersze
                for row in selected_rows:
                    if row < len(initial_books):  # Sprawdz czy indeks jest poprawny
                        book_id = initial_books[row][0]  # ID zaznaczonego rekordu
                        delete_book_from_database(book_id)
                initial_books = get_books_from_database()
                window["-BOOKS-"].update(values=initial_books)
                        
            if event == "-REFRESH":
                initial_books = get_books_from_database()
                data = []
                for book in initial_books:
                    data.append(list(book) + [sg.Button("Usun", key=f"-DELETE_{book[0]}")])

                window["-BOOKS-"].update(values=data)

            if event == "-SEARCH":
                isbn_number = values["-ISBN-"]

                isbn_number = ''.join(c for c in isbn_number if c.isdigit())

                if not isbn_number:
                    sg.popup("Numer ISBN powinien zawierac co najmniej jedna cyfre.", font=("Helvetica", 14))
                    continue

                book_data = fetch_book_data(isbn_number)

                if book_data:
                    popup_layout = [
                        [sg.Text(f"Numer ISBN: {book_data.get('isbn')}", font=("Helvetica", 14))],
                        [sg.Text(f"Tytul: {book_data.get('title')}", font=("Helvetica", 14))],
                        [sg.Text(f"Autor: {book_data.get('author')}", font=("Helvetica", 14))],
                        [sg.Text(f"Wydawca: {book_data.get('publisher')}", font=("Helvetica", 14))],
                        [sg.Text(f"Jezyk: {book_data.get('language')}", font=("Helvetica", 14))],
                        [sg.Button(image_filename="download.png", key="-DOWNLOAD", image_size=(30, 30))]
                    ]

                    popup_window = sg.Window("Dane ksiazki", popup_layout)

                    while True:
                        event, _ = popup_window.read()
                        if event == sg.WIN_CLOSED:
                            break
                        elif event == "-DOWNLOAD":
                            if not is_book_in_database(book_data.get("isbn")):
                                save_book_to_database(book_data)
                                sg.popup("Dane ksiazki zostaly zapisane do bazy danych.",font=("Helvetica", 14))
                                
                                # Aktualizacja tabeli po dodaniu ksiazki do bazy
                                window["-BOOKS-"].update(values=get_books_from_database())
                            else:
                                sg.popup("Ksiazka o podanym numerze ISBN już istnieje w bazie danych.", font=("Helvetica", 14))
                            popup_window.close()
                            break

        window.close()

    except Exception as e:
        print("Wystapil blad podczas laczenia z baza danych:", e)
    finally:
        if db_cursor is not None:
            db_cursor.close()
        if db_connection is not None:
            db_connection.close()

if __name__ == "__main__":
    main()