/**
 * Catalog search. Every search box in the app goes through here, so the
 * endpoint and result shape live in one place (see issue #14, and #9 for the
 * backend search upgrade).
 */
import { apiFetch } from "./api";

export type BookResult = {
  /** Database id. Club, schedule and other write endpoints expect this. */
  id: number;
  /** Open Library work id, used in URLs: /book/<book_id> */
  book_id: string;
  title: string;
  authors: string[];
  cover_image: string | null;
  year_published: number | null;
  summary?: string | null;
  genres?: string[];
};

export type AuthorResult = {
  author_id: string;
  name: string;
  author_image: string | null;
  biography?: string | null;
};

export type SearchResults = { books: BookResult[]; authors: AuthorResult[] };

export async function searchCatalog(
  query: string,
  { limit = 8, signal }: { limit?: number; signal?: AbortSignal } = {}
): Promise<SearchResults> {
  const q = query.trim();
  if (!q) return { books: [], authors: [] };

  const response = await apiFetch(
    `/api/search-bar/?q=${encodeURIComponent(q)}&limit=${limit}`,
    { signal }
  );
  if (!response.ok) throw new Error(`Search failed (${response.status})`);

  const data = await response.json();
  return {
    books: Array.isArray(data.books) ? data.books : [],
    authors: Array.isArray(data.authors) ? data.authors : [],
  };
}
