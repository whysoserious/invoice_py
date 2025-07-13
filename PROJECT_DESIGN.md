### **Dokument Projektowy: Automatyczny Procesor Faktur i Wyciągów Bankowych**

**Wersja:** 1.3
**Data:** 13.07.2025
**Autor:** Gemini

#### 1. Wprowadzenie i Cel Projektu

**Problem:** Ręczne przepisywanie danych z faktur i wyciągów bankowych w formacie PDF do systemów księgowych lub arkuszy kalkulacyjnych jest procesem czasochłonnym, monotonnym i podatnym na błędy. Wiele instytucji finansowych dostarcza wyciągi w formacie PDF, które często zawierają dane w formie obrazów lub w układzie trudnym do automatycznego parsowania standardowymi metodami.

**Cel:** Celem tego projektu jest stworzenie narzędzia wiersza poleceń (CLI), które zautomatyzuje proces ekstrakcji danych o transakcjach z plików PDF. Narzędzie wykorzysta zaawansowany, multimodalny model sztucznej inteligencji (Google Gemini) do analizy zarówno warstwy tekstowej, jak i wizualnej dokumentu, aby zapewnić wysoką dokładność. Wynikiem działania programu będzie ustrukturyzowany plik w formacie CSV, gotowy do dalszego importu lub analizy.

#### 2. Zakres Projektu
*   Przetwarzanie plików w formacie PDF.
*   Obsługa jednego pliku, listy plików lub całego folderu jako danych wejściowych.
*   Ekstrakcja kluczowych informacji o transakcjach: data, rachunek źródłowy/docelowy, kwota, saldo, opis.
*   Wykorzystanie zewnętrznego API (Google AI Platform) do analizy dokumentów za pomocą modelu Gemini.
*   Generowanie osobnego pliku `.csv` dla każdego przetworzonego pliku `.pdf`.
*   Obsługa za pomocą interfejsu wiersza poleceń (CLI).

#### 3. Wymagania Funkcjonalne
1.  **Interfejs Użytkownika:** Wymaga argumentów CLI (`--file`, `--folder`, `--api-key`).
2.  **Przetwarzanie Plików:** Weryfikuje istnienie plików/folderów i filtruje pliki `.pdf`.
3.  **Ekstrakcja Danych:** Konwertuje każdą stronę PDF na obraz i wyodrębnia z niej tekst.
4.  **Integracja z Modelem AI:** Przetwarza każdą stronę w osobnym zapytaniu, implementując logikę obsługi transakcji dzielonych między stronami.
5.  **Generowanie Wyników:** Agreguje wyniki ze wszystkich stron do jednego pliku CSV z predefiniowanymi kolumnami.

#### 4. Architektura i Projekt Techniczny

**Stos Technologiczny:**
*   **Język:** Python 3
*   **Kluczowe Biblioteki:** `argparse`, `os`, `sys`, `PyPDF2`, `pdf2image`, `Pillow`, `google-generativeai`, `base64`, `re`.

**Szablon Promptu dla Modelu AI (Gemini)**

Poniższy szablon zostanie użyty dla każdego zapytania wysyłanego do API. Został on zoptymalizowany pod kątem przetwarzania strona po stronie i obsługi transakcji dzielonych.

```
Jesteś precyzyjnym asystentem do ekstrakcji danych finansowych. Twoim zadaniem jest analiza strony wyciągu bankowego i wyodrębnienie z niej transakcji do formatu CSV.

### Kontekst
- Obraz bieżącej strony (Strona N): <image>{{CURRENT_PAGE_IMAGE}}</image>
- Tekst z bieżącej strony (Strona N): <text>{{CURRENT_PAGE_TEXT}}</text>
- Kontekst - ostatnia transakcja z poprzedniej strony (Strona N-1): <previous_transaction_context>{{PREVIOUS_TRANSACTION_CONTEXT}}</previous_transaction_context>
- Rok, którego dotyczy wyciąg (do uzupełnienia dat bez roku): {{YEAR_CONTEXT}}

### Instrukcje i Reguły
1.  **Analiza Kontekstu:** Sprawdź, czy pierwsza transakcja na bieżącej stronie (Strona N) jest kontynuacją transakcji z `previous_transaction_context`. Jeśli tak, połącz je w jeden kompletny wpis. Jeśli `previous_transaction_context` jest puste lub transakcja nie jest kontynuacją, traktuj ją jako nową.
2.  **Ekstrakcja Danych:** Wyodrębnij wszystkie kompletne transakcje widoczne na obrazie.
3.  **Reguły Formatowania:**
    - `data`: Zawsze w formacie YYYY-MM-DD. Jeśli na wyciągu brakuje roku, użyj `{{YEAR_CONTEXT}}`.
    - `kwoty` (suma, saldo): Używaj kropki (.) jako separatora dziesiętnego. Zwracaj tylko liczby, bez symboli walut i separatorów tysięcy (np. `1234.56`).
    - `numery kont` (od, do): Zwracaj jako ciąg cyfr, usuwając wszystkie spacje i myślniki.
4.  **Przypadki Brzegowe:**
    - **Brak transakcji:** Jeśli strona nie zawiera żadnych transakcji (np. jest to strona tytułowa lub podsumowanie), zwróć pusty tag `<csv_output></csv_output>`.
    - **Niekompletna transakcja na dole:** Nie uwzględniaj transakcji, która jest wyraźnie urwana na dole strony. Zostanie ona przetworzona w całości z następną stroną.
5.  **Format Wyjściowy:** Zwróć dane WYŁĄCZNIE wewnątrz tagów `<csv_output>`. Nie dodawaj żadnych wyjaśnień, wstępów ani podsumowań. Nagłówek CSV musi być zawsze obecny, nawet jeśli nie znaleziono transakcji.

### Przykład Formatu Wyjściowego
<csv_output>
data,od,do,suma przelewu,saldo przed,saldo po,opis transakcji
2023-05-01,123456789,987654321,1000.00,5000.00,4000.00,Payment for services
</csv_output>
```
*   **Objaśnienie placeholderów:**
    *   `{{CURRENT_PAGE_IMAGE}}`: Obraz bieżącej strony w formacie Base64.
    *   `{{CURRENT_PAGE_TEXT}}`: Tekst wyekstrahowany z bieżącej strony.
    *   `{{PREVIOUS_TRANSACTION_CONTEXT}}`: Dane ostatniej kompletnej transakcji z poprzedniej strony (w formacie CSV) lub pusta wartość.
    *   `{{YEAR_CONTEXT}}`: Rok, którego dotyczy wyciąg, np. "2024".

**Strategia Przetwarzania Stron i Obsługa Transakcji Dzielonych**

Zostanie zaimplementowany mechanizm "przesuwnego okna kontekstowego". Podczas przetwarzania strony `N` (dla `N > 1`), skrypt przekaże do modelu AI nie tylko obraz strony `N`, ale również kontekst z poprzedniej strony (ostatnią przetworzoną transakcję), używając powyższego szablonu promptu.

**Przepływ Pracy (Workflow):**

1.  **Inicjalizacja:** Uruchomienie skryptu z argumentami.
2.  **Walidacja Wejścia:** Sprawdzenie poprawności argumentów.
3.  **Pętla po Plikach:** Iteracja po każdym pliku PDF.
4.  **Faza Przygotowania Danych:** Konwersja PDF na listę obrazów, inicjalizacja pustej listy na wyniki i pustej zmiennej na kontekst.
5.  **Pętla po Stronach:** Dla każdej strony dokumentu:
    a.  **Konstrukcja Promptu:** Wypełnienie szablonu promptu obrazem bieżącej strony i kontekstem z poprzedniej.
    b.  **Wysłanie Zapytania:** Wysłanie danych do API Gemini.
    c.  **Przetwarzanie Wyniku:** Odebranie i sparsowanie odpowiedzi, aktualizacja/dodanie transakcji do listy wyników.
    d.  **Aktualizacja Kontekstu:** Zapisanie ostatniej transakcji z bieżącej strony jako kontekst dla następnej.
6.  **Agregacja i Zapis Pliku:** Zapisanie kompletnej listy transakcji do pliku `.csv`.
7.  **Zakończenie:** Koniec programu.

#### 5. Założenia i Zależności

*   Wymagana instalacja Pythona 3, `poppler` oraz bibliotek z `requirements.txt`.
*   Użytkownik musi posiadać aktywny klucz API do usług Google AI Platform.
*   Dokładność wyników zależy od jakości plików PDF i możliwości modelu AI.
