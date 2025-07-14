### **Dokument Projektowy: Automatyczny Procesor Faktur i Wyciągów Bankowych**

**Wersja:** 1.5
**Data:** 13.07.2025
**Autor:** Gemini

#### 1. Wprowadzenie i Cel Projektu

**Problem:** Ręczne przepisywanie i kategoryzowanie danych z faktur i wyciągów bankowych jest procesem czasochłonnym, monotonnym i podatnym na błędy.

**Cel:** Celem tego projektu jest stworzenie inteligentnego narzędzia wiersza poleceń (CLI), które w pełni automatyzuje proces ekstrakcji i kategoryzacji danych o transakcjach z plików PDF. Narzędzie wykorzysta zaawansowany, multimodalny model sztucznej inteligencji (Google Gemini) do analizy dokumentów, a jego działanie będzie można dostosować za pomocą prostych reguł. Wynikiem będzie ustrukturyzowany plik w formacie CSV lub JSON.

#### 2. Zakres Projektu i Kluczowe Funkcjonalności

*   **Ekstrakcja Danych z PDF:** Przetwarzanie plików PDF, obsługa jednego pliku, listy plików lub całego folderu.
*   **Integracja z AI:** Wykorzystanie API Google Gemini do analizy wizualnej i tekstowej dokumentów.
*   **Wsparcie dla Wielu Formatów Wyjściowych:** Możliwość generowania wyników w formacie `.csv` lub `.json` na podstawie wyboru użytkownika.
*   **Inteligentna Kategoryzacja Transakcji:** Automatyczne przypisywanie transakcji do predefiniowanych kategorii na podstawie analizy AI oraz reguł zdefiniowanych przez użytkownika.
*   **Interaktywny Tryb Weryfikacji:** Opcjonalny tryb, w którym aplikacja prosi użytkownika o potwierdzenie transakcji o niskim poziomie pewności.
*   **Zaawansowane Logowanie i Raportowanie:** Prowadzenie pliku `log` z przebiegu operacji i generowanie podsumowania po zakończeniu pracy.
*   **[NOWOŚĆ] Dokumentacja Projektu:** Wygenerowanie pliku `README.md` z kompleksową instrukcją instalacji, konfiguracji i użytkowania.

#### 3. Wymagania Funkcjonalne

1.  **Interfejs Użytkownika:**
    *   Wymaga argumentów CLI (`--file`, `--folder`, `--api-key`).
    *   Dodatkowe flagi: `--output-format [csv|json]`, `--interactive`.
2.  **Przetwarzanie Plików:** Weryfikuje istnienie plików/folderów i filtruje pliki `.pdf`.
3.  **Ekstrakcja i Kategoryzacja:**
    *   Konwertuje każdą stronę PDF na obraz i wyodrębnia z niej tekst.
    *   Przetwarza każdą stronę w osobnym zapytaniu, implementując logikę obsługi transakcji dzielonych.
    *   Dołącza do promptu prośbę o kategoryzację i reguły zdefiniowane przez użytkownika.
4.  **Generowanie Wyników:**
    *   Agreguje wyniki ze wszystkich stron do jednego pliku w wybranym formacie (CSV lub JSON).
    *   Plik wyjściowy zawiera dodatkową kolumnę `kategoria`.
5.  **Tryb Interaktywny:**
    *   Jeśli model AI zwróci transakcję z niskim progiem pewności (lub bez kategorii), a flaga `--interactive` jest aktywna, aplikacja wyświetli dane i poprosi użytkownika o potwierdzenie/poprawienie.
6.  **Logowanie:**
    *   Wszystkie operacje (odczyt pliku, zapytanie do API, zapis wyniku, błędy) są zapisywane w pliku `processing.log`.
    *   Po zakończeniu na konsoli wyświetlane jest zwięzłe podsumowanie.
7.  **[NOWOŚĆ] Generowanie Dokumentacji:**
    *   Stworzenie pliku `README.md` zawierającego: ogólny opis projektu, instrukcje instalacji zależności (`pip`, `poppler`), opis wszystkich argumentów CLI, przykłady użycia oraz wyjaśnienie formatu pliku z regułami (`rules.yaml`).

#### 4. Architektura i Projekt Techniczny

**Stos Technologiczny:**
*   **Język:** Python 3
*   **Kluczowe Biblioteki:** `argparse`, `os`, `sys`, `PyPDF2`, `pdf2image`, `Pillow`, `google-generativeai`, `base64`, `re`, `PyYAML` (do reguł użytkownika).

**Plik Konfiguracyjny (opcjonalny `rules.yaml`):**
Użytkownik będzie mógł stworzyć plik `rules.yaml` do definiowania własnych reguł kategoryzacji:
```yaml
rules:
  - if_description_contains: ["BP", "Orlen", "Circle K"]
    category: "Koszty: Paliwo"
  - if_description_contains: ["Biedronka", "Lidl"]
    category: "Wydatki: Spożywcze"
```

**Szablon Promptu dla Modelu AI (Gemini) - Zaktualizowany**

Poniższy szablon zostanie użyty dla każdego zapytania. Został rozszerzony o zadanie kategoryzacji.

```
Jesteś precyzyjnym asystentem do ekstrakcji i kategoryzacji danych finansowych. Twoim zadaniem jest analiza strony wyciągu bankowego i wyodrębnienie z niej transakcji.

### Kontekst
- Obraz bieżącej strony (Strona N): <image>{{CURRENT_PAGE_IMAGE}}</image>
- Tekst z bieżącej strony (Strona N): <text>{{CURRENT_PAGE_TEXT}}</text>
- Kontekst - ostatnia transakcja z poprzedniej strony (Strona N-1): <previous_transaction_context>{{PREVIOUS_TRANSACTION_CONTEXT}}</previous_transaction_context>
- Rok, którego dotyczy wyciąg: {{YEAR_CONTEXT}}
- Reguły użytkownika do kategoryzacji: <rules>{{USER_RULES}}</rules>

### Instrukcje i Reguły
1.  **Analiza Kontekstu:** Sprawdź, czy pierwsza transakcja na bieżącej stronie jest kontynuacją transakcji z `previous_transaction_context`. Jeśli tak, połącz je.
2.  **Ekstrakcja Danych:** Wyodrębnij wszystkie kompletne transakcje widoczne na obrazie.
3.  **Kategoryzacja:** Dla każdej transakcji przypisz kategorię. Najpierw sprawdź, czy opis pasuje do którejś z `USER_RULES`. Jeśli nie, przypisz jedną z domyślnych kategorii: [Przychody, Wydatki: Zakupy, Wydatki: Usługi, Opłaty Bankowe, Inne].
4.  **Reguły Formatowania:** Data w YYYY-MM-DD, kwoty z kropką dziesiętną, numery kont bez spacji.
5.  **Przypadki Brzegowe:** Zignoruj niekompletne transakcje na dole strony. Dla pustych stron zwróć pusty wynik.
6.  **Format Wyjściowy:** Zwróć dane WYŁĄCZNIE wewnątrz tagów `<output>`. Dołącz pole `kategoria`. Zwróć też pole `confidence` (0-1) oznaczające twoją pewność co do poprawności ekstrakcji.

### Przykład Formatu Wyjściowego
<output>
[  
  {
    "data": "2023-05-01",
    "od": "123456789",
    "do": "987654321",
    "suma_przelewu": 1000.00,
    "saldo_przed": 5000.00,
    "saldo_po": 4000.00,
    "opis_transakcji": "Payment for services",
    "kategoria": "Przychody",
    "confidence": 0.95
  }
]
</output>
```

**Przepływ Pracy (Workflow):**
1.  **Inicjalizacja:** Uruchomienie skryptu, wczytanie argumentów i opcjonalnych reguł z `rules.yaml`.
2.  **Pętla po Plikach i Stronach:** Przetwarzanie każdego pliku strona po stronie.
3.  **Konstrukcja i Wysłanie Promptu:** Wypełnienie szablonu i wysłanie zapytania do API Gemini.
4.  **Przetwarzanie Wyniku i Weryfikacja:**
    *   Odebranie i sparsowanie odpowiedzi.
    *   Jeśli flaga `--interactive` jest aktywna, a `confidence` którejś transakcji jest poniżej progu (np. 0.8), zapytaj użytkownika o potwierdzenie.
5.  **Agregacja i Zapis Pliku:** Zapisanie kompletnej listy transakcji do pliku `.csv` lub `.json`.
6.  **Logowanie i Zakończenie:** Zapisanie logów i wyświetlenie podsumowania.

#### 5. Założenia i Zależności

*   Wymagana instalacja Pythona 3, `poppler` oraz bibliotek z `requirements.txt`.
*   Użytkownik musi posiadać aktywny klucz API do usług Google AI Platform.
*   Dokładność wyników zależy od jakości plików PDF i możliwości modelu AI.
