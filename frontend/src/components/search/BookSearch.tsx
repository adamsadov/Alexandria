"use client";

/**
 * The one book search used everywhere in the app (issue #14).
 *
 * Two modes:
 *  - "pick"     choose a book for something (journal, club, schedule...).
 *               Results appear inline; picking calls onSelect. Pass `selected`
 *               and `onClear` to show the chosen book with a "Change" button.
 *  - "navigate" site search. Results appear in a dropdown; picking opens the
 *               book/author page and Enter goes to /search?q=...
 *
 *   <BookSearch mode="pick" selected={book} onSelect={setBook} onClear={() => setBook(null)} />
 *   <BookSearch mode="navigate" size="lg" />
 */
import {
  KeyboardEvent,
  MouseEvent as ReactMouseEvent,
  ReactNode,
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
} from "react";
import { useRouter } from "next/navigation";
import { BookOpen, Loader2, Search, User, X } from "lucide-react";
import { AuthorResult, BookResult, searchCatalog } from "@/lib/search";
import styles from "./BookSearch.module.css";

type Option =
  | { kind: "book"; book: BookResult }
  | { kind: "author"; author: AuthorResult }
  | { kind: "all" };

export type BookSearchProps = {
  mode?: "pick" | "navigate";
  onSelect?: (book: BookResult) => void;
  /** pick mode: the chosen book, shown as a card instead of the input */
  selected?: BookResult | null;
  onClear?: () => void;
  /** Also search authors (default: on in navigate mode) */
  includeAuthors?: boolean;
  /** "dropdown" floats over the page; "inline" pushes content down (best in modals) */
  variant?: "dropdown" | "inline";
  size?: "md" | "lg";
  label?: string;
  showLabel?: boolean;
  placeholder?: string;
  autoFocus?: boolean;
  disabled?: boolean;
  limit?: number;
  initialQuery?: string;
  /** Shown under the input, e.g. a validation message */
  error?: string;
  className?: string;
};

const DEBOUNCE_MS = 300;

export function BookSearch({
  mode = "pick",
  onSelect,
  selected = null,
  onClear,
  includeAuthors,
  variant,
  size = "md",
  label = "Search books",
  showLabel = false,
  placeholder = "Search by title, author or ISBN",
  autoFocus = false,
  disabled = false,
  limit = 8,
  initialQuery = "",
  error,
  className,
}: BookSearchProps) {
  const router = useRouter();
  const navigate = mode === "navigate";
  const withAuthors = includeAuthors ?? navigate;
  const layout = variant ?? (navigate ? "dropdown" : "inline");

  const [query, setQuery] = useState(initialQuery);
  const [books, setBooks] = useState<BookResult[]>([]);
  const [authors, setAuthors] = useState<AuthorResult[]>([]);
  const [status, setStatus] = useState<"idle" | "loading" | "done" | "error">("idle");
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);
  const [retry, setRetry] = useState(0);

  const rootRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const listId = useId();
  const inputId = useId();

  // Search as you type: debounce, and abort any request that's been overtaken.
  useEffect(() => {
    const q = query.trim();
    if (!q) {
      setBooks([]);
      setAuthors([]);
      setStatus("idle");
      return;
    }
    setStatus("loading");
    const controller = new AbortController();
    const timer = setTimeout(async () => {
      try {
        const results = await searchCatalog(q, { limit, signal: controller.signal });
        setBooks(results.books);
        setAuthors(withAuthors ? results.authors : []);
        setStatus("done");
        setActive(-1);
      } catch (err) {
        if ((err as Error).name !== "AbortError") setStatus("error");
      }
    }, DEBOUNCE_MS);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [query, limit, withAuthors, retry]);

  // Close the dropdown when clicking anywhere else.
  useEffect(() => {
    if (layout !== "dropdown") return;
    const onDown = (e: MouseEvent) => {
      if (!rootRef.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onDown);
    return () => document.removeEventListener("mousedown", onDown);
  }, [layout]);

  const options: Option[] = useMemo(() => {
    const list: Option[] = books.map((book) => ({ kind: "book" as const, book }));
    authors.forEach((author) => list.push({ kind: "author", author }));
    if (navigate && query.trim()) list.push({ kind: "all" });
    return list;
  }, [books, authors, navigate, query]);

  const goToSearchPage = () => {
    const q = query.trim();
    if (!q) return;
    setOpen(false);
    router.push(`/search?q=${encodeURIComponent(q)}`);
  };

  const choose = (option: Option) => {
    if (option.kind === "all") return goToSearchPage();
    if (option.kind === "author") {
      setOpen(false);
      return router.push(`/author/${option.author.author_id}`);
    }
    if (navigate) {
      setOpen(false);
      router.push(`/book/${option.book.book_id}`);
    } else {
      onSelect?.(option.book);
      setQuery("");
      setOpen(false);
    }
  };

  const onKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "ArrowDown" && options.length) {
      e.preventDefault();
      setOpen(true);
      setActive((i) => (i + 1) % options.length);
    } else if (e.key === "ArrowUp" && options.length) {
      e.preventDefault();
      setOpen(true);
      setActive((i) => (i <= 0 ? options.length - 1 : i - 1));
    } else if (e.key === "Enter") {
      // Never submit a surrounding <form> from the search box.
      e.preventDefault();
      if (active >= 0 && options[active]) choose(options[active]);
      else if (navigate) goToSearchPage();
      else if (books.length === 1) choose({ kind: "book", book: books[0] });
    } else if (e.key === "Escape") {
      if (open && layout === "dropdown") setOpen(false);
      else setQuery("");
      setActive(-1);
    }
  };

  // ---- pick mode with a book already chosen: show it instead of the input
  if (!navigate && selected) {
    return (
      <div className={cx(styles.root, className)}>
        {showLabel && <span className={styles.label}>{label}</span>}
        <div className={styles.selected}>
          <Cover src={selected.cover_image} alt="" large />
          <div className={styles.meta}>
            <span className={styles.selectedTitle}>{selected.title}</span>
            <span className={styles.authors}>{byline(selected.authors)}</span>
            {selected.year_published ? (
              <span className={styles.year}>{selected.year_published}</span>
            ) : null}
          </div>
          {onClear && (
            <button
              type="button"
              className={styles.changeButton}
              onClick={() => {
                onClear();
                requestAnimationFrame(() => inputRef.current?.focus());
              }}
              disabled={disabled}
            >
              Change
            </button>
          )}
        </div>
      </div>
    );
  }

  const q = query.trim();
  const showPanel = !!q && (layout === "inline" || open);
  const activeId = active >= 0 ? `${listId}-opt-${active}` : undefined;
  const bookCount = books.length;

  return (
    <div
      ref={rootRef}
      className={cx(styles.root, size === "lg" && styles.lg, className)}
    >
      <label htmlFor={inputId} className={showLabel ? styles.label : styles.srOnly}>
        {label}
      </label>
      <div className={styles.inputRow}>
        <div className={cx(styles.inputWrap, error && styles.inputError)}>
          <Search className={styles.searchIcon} aria-hidden />
          <input
            ref={inputRef}
            id={inputId}
            className={styles.input}
            type="text"
            inputMode="search"
            enterKeyHint="search"
            autoComplete="off"
            spellCheck={false}
            role="combobox"
            aria-expanded={showPanel}
            aria-controls={listId}
            aria-autocomplete="list"
            aria-activedescendant={activeId}
            aria-invalid={!!error}
            placeholder={placeholder}
            value={query}
            autoFocus={autoFocus}
            disabled={disabled}
            onChange={(e) => {
              setQuery(e.target.value);
              setOpen(true);
            }}
            onFocus={() => setOpen(true)}
            onKeyDown={onKeyDown}
          />
          {status === "loading" && <Loader2 className={styles.spinner} aria-hidden />}
          {query && status !== "loading" && (
            <button
              type="button"
              className={styles.clearButton}
              aria-label="Clear search"
              onClick={() => {
                setQuery("");
                inputRef.current?.focus();
              }}
            >
              <X aria-hidden />
            </button>
          )}
        </div>
        {navigate && (
          <button
            type="button"
            className={styles.submitButton}
            onClick={goToSearchPage}
            disabled={!q}
            aria-label="Show all results"
          >
            <Search aria-hidden />
            <span className={styles.submitText}>Search</span>
          </button>
        )}
      </div>

      {error && <p className={styles.errorText}>{error}</p>}

      <p className={styles.srOnly} aria-live="polite">
        {status === "done" && q
          ? `${bookCount} book${bookCount === 1 ? "" : "s"} found`
          : ""}
      </p>

      {showPanel && (
        <div className={cx(styles.panel, layout === "dropdown" ? styles.dropdown : styles.inline)}>
          {status === "error" ? (
            <div className={styles.message}>
              Search isn&apos;t working right now.
              <button type="button" className={styles.linkButton} onClick={() => setRetry((n) => n + 1)}>
                Try again
              </button>
            </div>
          ) : status === "loading" && options.length === 0 ? (
            <ul className={styles.list} aria-hidden>
              {[0, 1, 2].map((i) => (
                <li key={i} className={styles.skeletonRow}>
                  <span className={styles.skeletonCover} />
                  <span className={styles.skeletonLines}>
                    <span />
                    <span />
                  </span>
                </li>
              ))}
            </ul>
          ) : status === "done" && books.length === 0 && authors.length === 0 ? (
            <div className={styles.message}>
              No books found for &ldquo;{q}&rdquo;. Try a different title, author or ISBN.
            </div>
          ) : (
            <ul id={listId} role="listbox" className={styles.list} aria-label={label}>
              {options.map((option, index) => {
                const props = {
                  id: `${listId}-opt-${index}`,
                  role: "option" as const,
                  "aria-selected": index === active,
                  className: cx(styles.option, index === active && styles.active),
                  onMouseDown: (e: ReactMouseEvent) => e.preventDefault(), // keep focus in input
                  onMouseEnter: () => setActive(index),
                  onClick: () => choose(option),
                };
                const heading =
                  withAuthors && option.kind === "author" && index === bookCount ? (
                    <li role="presentation" className={styles.groupHeading}>
                      Authors
                    </li>
                  ) : withAuthors && index === 0 && option.kind === "book" ? (
                    <li role="presentation" className={styles.groupHeading}>
                      Books
                    </li>
                  ) : null;

                if (option.kind === "book") {
                  const b = option.book;
                  return (
                    <Row key={`b-${b.id ?? b.book_id}`} heading={heading}>
                      <li {...props}>
                        <Cover src={b.cover_image} alt="" />
                        <span className={styles.meta}>
                          <span className={styles.title}>{highlight(b.title, q)}</span>
                          <span className={styles.authors}>{byline(b.authors)}</span>
                          {b.year_published ? (
                            <span className={styles.year}>{b.year_published}</span>
                          ) : null}
                        </span>
                      </li>
                    </Row>
                  );
                }
                if (option.kind === "author") {
                  const a = option.author;
                  return (
                    <Row key={`a-${a.author_id}`} heading={heading}>
                      <li {...props}>
                        <span className={styles.avatar}>
                          {a.author_image ? (
                            <img src={a.author_image} alt="" loading="lazy" />
                          ) : (
                            <User aria-hidden />
                          )}
                        </span>
                        <span className={styles.meta}>
                          <span className={styles.title}>{highlight(a.name, q)}</span>
                          <span className={styles.authors}>Author</span>
                        </span>
                      </li>
                    </Row>
                  );
                }
                return (
                  <li key="all" {...props} className={cx(props.className, styles.seeAll)}>
                    <Search aria-hidden />
                    See all results for &ldquo;{q}&rdquo;
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}

export default BookSearch;

/**
 * The same search input, without catalog results: for filtering a list that's
 * already on the page (e.g. book clubs), so every search box looks alike.
 */
export function SearchField({
  value,
  onChange,
  label = "Search",
  placeholder = "Search",
  size = "md",
  className,
}: {
  value: string;
  onChange: (value: string) => void;
  label?: string;
  placeholder?: string;
  size?: "md" | "lg";
  className?: string;
}) {
  const inputId = useId();
  const inputRef = useRef<HTMLInputElement>(null);
  return (
    <div className={cx(styles.root, size === "lg" && styles.lg, className)}>
      <label htmlFor={inputId} className={styles.srOnly}>
        {label}
      </label>
      <div className={styles.inputWrap}>
        <Search className={styles.searchIcon} aria-hidden />
        <input
          ref={inputRef}
          id={inputId}
          className={styles.input}
          type="text"
          inputMode="search"
          enterKeyHint="search"
          autoComplete="off"
          placeholder={placeholder}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Escape") onChange("");
          }}
        />
        {value && (
          <button
            type="button"
            className={styles.clearButton}
            aria-label="Clear search"
            onClick={() => {
              onChange("");
              inputRef.current?.focus();
            }}
          >
            <X aria-hidden />
          </button>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------- helpers

function Row({ heading, children }: { heading: ReactNode; children: ReactNode }) {
  return (
    <>
      {heading}
      {children}
    </>
  );
}

function Cover({ src, alt, large = false }: { src: string | null; alt: string; large?: boolean }) {
  const [failed, setFailed] = useState(false);
  return (
    <span className={cx(styles.cover, large && styles.coverLarge)}>
      {src && !failed ? (
        <img src={src} alt={alt} loading="lazy" onError={() => setFailed(true)} />
      ) : (
        <BookOpen aria-hidden />
      )}
    </span>
  );
}

function byline(authors: string[] | undefined) {
  if (!authors || authors.length === 0) return "Unknown author";
  return authors.length > 2 ? `${authors.slice(0, 2).join(", ")} +${authors.length - 2}` : authors.join(", ");
}

/** Bold the part of `text` that matches the query. */
function highlight(text: string, q: string) {
  const i = text.toLowerCase().indexOf(q.toLowerCase());
  if (!q || i < 0) return text;
  return (
    <>
      {text.slice(0, i)}
      <mark className={styles.match}>{text.slice(i, i + q.length)}</mark>
      {text.slice(i + q.length)}
    </>
  );
}

function cx(...names: (string | false | null | undefined)[]) {
  return names.filter(Boolean).join(" ");
}
