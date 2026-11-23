"use client";

import React, { useState, useEffect } from "react";
import { useSession } from "@/lib/session";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { BookOpen, PlusCircle } from "lucide-react";
import Image from "next/image";
import { apiFetch } from "@/lib/api";
import { BookSearch } from "@/components/search/BookSearch";
import type { BookResult } from "@/lib/search";

// Type definitions
interface Book {
  book_id: string;
  title: string;
  authors: string[];
  cover_url?: string;
  year_published?: number;
  summary?: string;
}

interface BookDetails {
  id: number;
  book_id: string;
  title: string;
  authors: string[];
  year_published: number;
  summary?: string;
  cover_url?: string;
}

interface ClubBook {
  id: number;
  book: string | number;
  book_details: BookDetails;
}

interface BooksTabProps {
  clubData: any;
  clubId: string;
  isAdmin: boolean;
  onRefresh: () => void;
}

export function BooksTab({
  clubData,
  clubId,
  isAdmin,
  onRefresh,
}: BooksTabProps) {
  // State for books and UI
  const [clubBooks, setClubBooks] = useState<ClubBook[]>([]);
  const [currentBook, setCurrentBook] = useState<ClubBook | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // State for book addition
  const [isAddBookDialogOpen, setIsAddBookDialogOpen] =
    useState<boolean>(false);
  const [selectedBook, setSelectedBook] = useState<BookResult | null>(null);

  const { isAuthenticated } = useSession();


  // Fetch club books whenever sign-in state or clubId changes
  useEffect(() => {
    if (isAuthenticated && clubId) {
      fetchClubBooks();
    }
  }, [isAuthenticated, clubId]);

  // Extract current book from club data if available
  useEffect(() => {
    if (clubData && clubData.book && clubData.book_details) {
      setCurrentBook({
        id: 0,
        book: clubData.book,
        book_details: clubData.book_details,
      });
    }
  }, [clubData]);

  // Function to fetch club reading history (which contains books)
  const fetchClubBooks = async () => {
    try {
      setLoading(true);
      setError(null);



      const response = await apiFetch(
        `/api/bookclubs/clubs/${clubId}/history/`,
        {
          headers: {
            "Content-Type": "application/json",
          },
        }
      );

      if (!response.ok) {
        throw new Error(`Failed to fetch club books: ${response.status}`);
      }

      const data = await response.json();
      setClubBooks(data);
    } catch (err) {
      console.error("Error fetching club books:", err);
      setError("Failed to load club books. Please try again later.");
    } finally {
      setLoading(false);
    }
  };

  // update the club's current book
  const handleAddBookToClub = async () => {
    if (!selectedBook) return;

    try {
      setError(null);


      const bookIdValue = selectedBook.book_id;
      if (!bookIdValue) {
        setError(`Invalid book ID: ${bookIdValue}. Book ID is required.`);
        return;
      }

      const requestData = {
        book_id: bookIdValue,
        title: selectedBook.title,
      };

      const response = await apiFetch(
        `/api/bookclubs/clubs/${clubId}/update-book/`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(requestData),
        }
      );

      const responseText = await response.text();

      try {
        const responseData = JSON.parse(responseText);

        if (responseData.success) {
          // Update current book with the response data
          setCurrentBook({
            id: 0,
            book: responseData.book_id,
            book_details: responseData.book_details,
          });

          // Close dialog and reset form
          setIsAddBookDialogOpen(false);
          setSelectedBook(null);

          // Refresh parent component
          if (typeof onRefresh === "function") {
            onRefresh(true);
          }
        } else if (responseData.error) {
          setError(responseData.message || responseData.error);
          return;
        }
      } catch (e) {
        console.error("Failed to parse response as JSON", e);
        setError("Failed to process server response. Please try again.");
        return;
      }

      if (!response.ok) {
        throw new Error(`Failed to update club book: ${response.status}`);
      }
    } catch (err) {
      console.error("Error updating club book:", err);
      setError(
        err.message || "Failed to update club book. Please try again later."
      );
    }
  };

  // Loading state
  if (loading) {
    return (
      <div className="text-amber-800 p-4 text-center">
        Loading book information...
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h3 className="text-xl font-serif font-bold text-amber-900">Books</h3>

        {/* Only show add book button for admins */}
        {isAdmin && (
          <Button
            onClick={() => setIsAddBookDialogOpen(true)}
            className="bg-amber-800 hover:bg-amber-700 text-amber-50"
          >
            <PlusCircle className="mr-2 h-4 w-4" />
            Add Book to Club
          </Button>
        )}
      </div>

      {/* Current Book Section */}
      <div>
        <h4 className="text-lg font-medium text-amber-800 mb-3">
          Current Book
        </h4>

        {currentBook ? (
          <Card className="border-amber-300 bg-amber-50">
            <CardHeader>
              <div className="flex items-start">
                {/* Cover image display */}
                <div className="w-16 h-20 bg-amber-200 rounded overflow-hidden flex items-center justify-center mr-4">
                  {currentBook.book_details.cover_url ? (
                    <Image
                      src={currentBook.book_details.cover_url}
                      alt={currentBook.book_details.title}
                      width={64}
                      height={80}
                      className="h-full w-full object-cover"
                    />
                  ) : (
                    <BookOpen className="h-8 w-8 text-amber-700" />
                  )}
                </div>

                <div>
                  <CardTitle className="text-amber-900">
                    {currentBook.book_details.title} (
                    {currentBook.book_details.year_published || "N/A"})
                  </CardTitle>
                  <div className="text-sm text-amber-700 mt-1">
                    by{" "}
                    {Array.isArray(currentBook.book_details.authors)
                      ? currentBook.book_details.authors.join(", ")
                      : currentBook.book_details.authors || "Unknown Author"}
                  </div>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <p className="text-amber-800">
                {currentBook.book_details.summary ||
                  "No summary available for this book."}
              </p>
            </CardContent>
          </Card>
        ) : (
          <div className="text-amber-700 bg-amber-100 p-4 rounded-md">
            No book is currently selected for this club.
            {isAdmin && (
              <div className="mt-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setIsAddBookDialogOpen(true)}
                  className="border-amber-300 text-amber-800"
                >
                  <PlusCircle className="mr-1 h-4 w-4" />
                  Add Book
                </Button>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Previously Read Books Section */}
      {clubBooks.length > 0 && (
        <div className="mt-8">
          <h4 className="text-lg font-medium text-amber-800 mb-3">
            Previously Read Books
          </h4>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {clubBooks.map((book) => (
              <Card key={book.id} className="border-amber-200 bg-amber-50">
                <CardHeader className="pb-2">
                  <div className="flex items-start">
                    {/* Cover image for history books */}
                    <div className="w-12 h-16 bg-amber-200 rounded overflow-hidden flex items-center justify-center mr-3">
                      {book.book_details.cover_url ? (
                        <Image
                          src={book.book_details.cover_url}
                          alt={book.book_details.title}
                          width={48}
                          height={64}
                          className="h-full w-full object-cover"
                        />
                      ) : (
                        <BookOpen className="h-6 w-6 text-amber-700" />
                      )}
                    </div>
                    <div>
                      <CardTitle className="text-amber-900 text-base">
                        {book.book_details.title} (
                        {book.book_details.year_published || "N/A"})
                      </CardTitle>
                      <div className="text-sm text-amber-700">
                        by {book.book_details.authors.join(", ")}
                      </div>
                    </div>
                  </div>
                </CardHeader>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* Add Book Dialog */}
      <Dialog open={isAddBookDialogOpen} onOpenChange={setIsAddBookDialogOpen}>
        <DialogContent className="bg-amber-50">
          <DialogHeader>
            <DialogTitle className="text-amber-900">
              Add Book to Club
            </DialogTitle>
            <DialogDescription className="text-amber-700">
              Search for a book to add to your book club.
            </DialogDescription>
          </DialogHeader>

          {error && (
            <div className="mb-4 text-red-600 text-sm p-2 bg-red-50 rounded">
              {error}
            </div>
          )}

          <div className="space-y-4">
            <BookSearch
              mode="pick"
              label="Search for a book"
              showLabel
              autoFocus
              selected={selectedBook}
              onSelect={setSelectedBook}
              onClear={() => setSelectedBook(null)}
            />

            <div className="flex justify-end space-x-2 pt-2">
              <Button
                variant="outline"
                onClick={() => {
                  setIsAddBookDialogOpen(false);
                  setSelectedBook(null);
                }}
                className="border-amber-300 text-amber-800"
              >
                Cancel
              </Button>
              <Button
                onClick={handleAddBookToClub}
                disabled={!selectedBook}
                className="bg-amber-800 text-amber-50"
              >
                Add to Club
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
