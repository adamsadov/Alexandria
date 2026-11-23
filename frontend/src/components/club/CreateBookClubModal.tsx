"use client";

import { useState, useEffect, useRef } from "react";
import { Button } from "../ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "../ui/checkbox";
import { Label } from "../ui/label";
import { useSession } from "@/lib/session";
import { X, Image as ImageIcon } from "lucide-react";
import Image from "next/image";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { apiFetch } from "@/lib/api";
import { BookSearch } from "@/components/search/BookSearch";
import type { BookResult } from "@/lib/search";

interface CreateBookClubModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function CreateBookClubModal({
  isOpen,
  onClose,
}: CreateBookClubModalProps) {
  const [name, setName] = useState<string>("");
  const [description, setDescription] = useState<string>("");
  const [isPrivate, setIsPrivate] = useState<boolean>(false);
  const [selectedBook, setSelectedBook] = useState<BookResult | null>(null);
  const [step, setStep] = useState<number>(1); // 1: Club details, 2: Book selection
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Image upload related states
  const [clubImage, setClubImage] = useState<File | null>(null);
  const [clubImagePreview, setClubImagePreview] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const { isAuthenticated } = useSession();
  const router = useRouter();


  // Reset form when modal is opened
  useEffect(() => {
    if (isOpen) {
      setName("");
      setDescription("");
      setIsPrivate(false);
      setSelectedBook(null);
      setStep(1);
      setError(null);
      setClubImage(null);
      setClubImagePreview(null);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleImageUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Check file type and size
    const validTypes = ["image/jpeg", "image/png", "image/gif"];
    if (!validTypes.includes(file.type)) {
      setError("Please upload a valid image file (JPEG, PNG, or GIF)");
      return;
    }

    if (file.size > 5 * 1024 * 1024) {
      // 5MB limit
      setError("Image size should be less than 5MB");
      return;
    }

    setClubImage(file);
    const imageUrl = URL.createObjectURL(file);
    setClubImagePreview(imageUrl);
    setError(null);
  };

  const handleRemoveImage = () => {
    setClubImage(null);
    setClubImagePreview(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const triggerFileInput = () => {
    if (fileInputRef.current) {
      fileInputRef.current.click();
    }
  };

  const handleSubmit = async () => {
    // Validate form
    if (!name.trim()) {
      setError("Club name is required");
      return;
    }

    try {
      setIsSubmitting(true);
      setError(null);



      const clubData = {
        name,
        club_desc: description,
        is_private: isPrivate,
        book: selectedBook?.id ?? null,
      };

      const response = await apiFetch(
        "/api/bookclubs/clubs/create/",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(clubData),
        }
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || "Failed to create book club");
      }

      const createdClub = await response.json();

      // If we have a club image, upload it after club creation
      if (clubImage && createdClub.id) {
        try {
          const formData = new FormData();
          formData.append("club_image", clubImage);

          const imageResponse = await apiFetch(
            `/api/bookclubs/clubs/${createdClub.id}/update-image/`,
            {
              method: "POST",
              headers: {
              },
              body: formData,
            }
          );

          if (!imageResponse.ok) {
            console.error("Failed to upload club image, but club was created");
          }
        } catch (imageErr) {
          console.error("Error uploading club image:", imageErr);
        }
      }

      // Close modal and navigate to the new club
      onClose();
      router.push(`/club/${createdClub.id}`);
    } catch (err) {
      console.error("Error creating book club:", err);
      setError(
        err instanceof Error ? err.message : "Failed to create book club"
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className="relative w-full max-w-2xl rounded-lg bg-amber-50 p-6 shadow-lg">
        <button
          onClick={onClose}
          className="absolute right-4 top-4 text-amber-700 hover:text-amber-900"
        >
          <X className="h-6 w-6" />
        </button>

        <h2 className="mb-6 text-2xl font-serif font-bold text-amber-900">
          {step === 1 ? "Create New Book Club" : "Select a Book (Optional)"}
        </h2>

        {error && (
          <div className="mb-4 rounded-md bg-red-100 p-3 text-red-700">
            {error}
          </div>
        )}

        {step === 1 ? (
          // Step 1: Club Details
          <div className="space-y-4">
            <div>
              <Label htmlFor="club-name" className="text-amber-800">
                Club Name *
              </Label>
              <Input
                id="club-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="border-amber-300 bg-white focus-visible:ring-amber-600"
                placeholder="Enter a name for your book club"
                required
              />
            </div>

            <div>
              <Label htmlFor="club-description" className="text-amber-800">
                Description
              </Label>
              <Textarea
                id="club-description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className="border-amber-300 bg-white focus-visible:ring-amber-600"
                placeholder="Describe what your club is about..."
                rows={4}
              />
            </div>

            {/* Club Image Upload */}
            <div>
              <Label htmlFor="club-image" className="text-amber-800">
                Club Image
              </Label>
              <input
                ref={fileInputRef}
                type="file"
                id="club-image"
                accept="image/*"
                onChange={handleImageUpload}
                className="hidden"
              />
              {clubImagePreview ? (
                <div className="mt-2 relative">
                  <div className="relative h-40 w-full rounded-md overflow-hidden border border-amber-300">
                    <Image
                      src={clubImagePreview}
                      alt="Club image preview"
                      layout="fill"
                      objectFit="cover"
                      className="w-full h-full object-cover"
                    />
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    className="absolute top-2 right-2 bg-amber-50 border-amber-300 text-amber-800"
                    onClick={handleRemoveImage}
                  >
                    <X className="h-4 w-4" />
                    <span className="ml-1">Remove</span>
                  </Button>
                </div>
              ) : (
                <div
                  onClick={triggerFileInput}
                  className="mt-2 flex flex-col items-center justify-center h-40 border-2 border-dashed border-amber-300 rounded-md bg-amber-50 cursor-pointer hover:bg-amber-100"
                >
                  <ImageIcon className="h-8 w-8 text-amber-600 mb-2" />
                  <p className="text-sm text-amber-700">
                    Click to upload a club image
                  </p>
                  <p className="text-xs text-amber-600 mt-1">
                    (Max size: 5MB, JPEG/PNG/GIF)
                  </p>
                </div>
              )}
            </div>

            <div className="flex items-center space-x-2">
              <Checkbox
                id="is-private"
                checked={isPrivate}
                onCheckedChange={(checked) => setIsPrivate(checked as boolean)}
                className="border-amber-400 data-[state=checked]:bg-amber-600"
              />
              <Label htmlFor="is-private" className="text-amber-800">
                Make this club private
              </Label>
            </div>

            <div className="mt-6 flex justify-end space-x-3">
            <motion.div 
                    whileHover={{ scale: 1.07 }}
                    whileTap={{ scale: 0.9 }}  
                > 
                <Button
                  variant="outline"
                  onClick={onClose}
                  className="border-amber-300 text-amber-800 rounded-full"
                >
                  Cancel
                </Button>
              </motion.div>
              <motion.div 
                  whileHover={{ scale: 1.07 }}
                  whileTap={{ scale: 0.9 }}  
              > 
                <Button
                  onClick={() => setStep(2)}
                  className="bg-amber-700 text-amber-50 hover:bg-amber-900 rounded-full"
                >
                  Next: Select Book
                </Button>
              </motion.div>
            </div>
          </div>
        ) : (
          // Step 2: Book Selection
          <div>
            <div className="mb-6">
              <BookSearch
                mode="pick"
                label="Choose the book your club will read"
                showLabel
                autoFocus
                selected={selectedBook}
                onSelect={setSelectedBook}
                onClear={() => setSelectedBook(null)}
              />
            </div>

            <div className="mt-6 flex items-center justify-between">
              <p className="text-sm text-amber-700">
                {!selectedBook &&
                  "You can create a club without selecting a book."}
              </p>

              <div className="flex space-x-3">
              <motion.div 
                    whileHover={{ scale: 1.07 }}
                    whileTap={{ scale: 0.9 }}  
                > 
                  <Button
                    variant="outline"
                    onClick={() => setStep(1)}
                    className="border-amber-300 text-amber-800 rounded-full"
                  >
                    Back
                  </Button>
                </motion.div>
                <motion.div 
                    whileHover={{ scale: 1.07 }}
                    whileTap={{ scale: 0.9 }}  
                > 
                  <Button
                    onClick={handleSubmit}
                    disabled={isSubmitting}
                    className="bg-amber-700 text-amber-50 hover:bg-amber-900 rounded-full"
                  >
                    {isSubmitting ? "Creating..." : "Create Book Club"}
                  </Button>
                </motion.div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
