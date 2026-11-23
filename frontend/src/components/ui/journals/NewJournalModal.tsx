"use client"

import { useState, useEffect } from "react"
import { Book, Plus, Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
} from "@/components/ui/dialog"
import { Label } from "@/components/ui/label"
import { Checkbox } from "@/components/ui/checkbox"
import { toast } from "@/hooks/use-toast"
import { useSession } from "@/lib/session";
import { apiFetch } from "@/lib/api";
import { BookSearch } from "@/components/search/BookSearch";
import type { BookResult } from "@/lib/search";

interface NewJournalModalProps {
    onJournalCreated?: () => void
}

export function NewJournalModal({ onJournalCreated }: NewJournalModalProps) {
    const [open, setOpen] = useState(false)
    const [selectedBook, setSelectedBook] = useState<BookResult | null>(null)
    const [isPrivate, setIsPrivate] = useState(false)
    const [isCreating, setIsCreating] = useState(false)
    const [errors, setErrors] = useState<Record<string, string>>({})
    const { isAuthenticated } = useSession();

    useEffect(() => {
        if (!open) {
            resetForm()
        }
    }, [open])

    const resetForm = () => {
        setSelectedBook(null)
        setIsPrivate(false)
        setErrors({})
    }

    const handleBookSelect = (book: BookResult) => {
        setSelectedBook(book)
        if (errors.book) {
            setErrors(prev => ({ ...prev, book: "" }))
        }
    }

    const validateForm = () => {
        const newErrors: Record<string, string> = {}

        if (!selectedBook) {
            newErrors.book = "Please select a book for your journal"
        }

        setErrors(newErrors)
        return Object.keys(newErrors).length === 0
    }

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()

        if (!validateForm()) {
            return
        }

        try {
            setIsCreating(true)


            const journalData = {
                book: selectedBook!.book_id,
                is_private: isPrivate
            }

            const response = await apiFetch('/api/journals/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(journalData)
            })

            if (!response.ok) {
                const errorData = await response.json()
                console.error('Journal creation failed:', errorData)
                
                // Handle validation errors from backend
                if (response.status === 400 && errorData) {
                    const backendErrors: Record<string, string> = {}
                    Object.keys(errorData).forEach(key => {
                        if (Array.isArray(errorData[key])) {
                            backendErrors[key] = errorData[key][0]
                        } else {
                            backendErrors[key] = errorData[key]
                        }
                    })
                    setErrors(backendErrors)
                    return
                }
                
                throw new Error(errorData.detail || `Failed to create journal: ${response.status}`)
            }

            const createdJournal = await response.json()

            // Reset form and close modal
            resetForm()
            setOpen(false)
            
            if (onJournalCreated) {
                onJournalCreated()
            }

        } catch (err) {
            console.error('Error creating journal:', err)
            toast({
                title: "Error",
                description: err instanceof Error ? err.message : "Failed to create journal. Please try again.",
                variant: "destructive",
            })
        } finally {
            setIsCreating(false)
        }
    }

    return (
        <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
                <Button className="gap-2">
                    <Plus className="w-4 h-4" />
                    New Journal
                </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-[600px] max-h-[80vh] overflow-y-auto">
                <DialogHeader>
                    <DialogTitle>Create New Reading Journal</DialogTitle>
                    <DialogDescription>
                        Search for a book and start documenting your reading journey.
                    </DialogDescription>
                </DialogHeader>
                
                <form onSubmit={handleSubmit} className="space-y-6">
                    {/* Book Search Section */}
                    <div className="space-y-4">
                        <BookSearch
                            mode="pick"
                            label="Select a book *"
                            showLabel
                            autoFocus
                            selected={selectedBook}
                            onSelect={handleBookSelect}
                            onClear={() => setSelectedBook(null)}
                            disabled={isCreating}
                            error={errors.book}
                        />
                    </div>

                    {/* Privacy Setting */}
                    <div className="flex items-center space-x-2">
                        <Checkbox
                            id="is_private"
                            checked={isPrivate}
                            onCheckedChange={(checked) => setIsPrivate(!!checked)}
                            disabled={isCreating}
                        />
                        <Label 
                            htmlFor="is_private" 
                            className="text-sm font-normal cursor-pointer"
                        >
                            Make this journal private
                        </Label>
                    </div>

                    <DialogFooter>
                        <Button 
                            type="button" 
                            variant="outline" 
                            onClick={() => setOpen(false)}
                            disabled={isCreating}
                        >
                            Cancel
                        </Button>
                        <Button 
                            type="submit" 
                            disabled={isCreating || !selectedBook}
                            className="gap-2"
                        >
                            {isCreating ? (
                                <>
                                    <Loader2 className="w-4 h-4 animate-spin" />
                                    Creating...
                                </>
                            ) : (
                                <>
                                    <Book className="w-4 h-4" />
                                    Create Journal
                                </>
                            )}
                        </Button>
                    </DialogFooter>
                </form>
            </DialogContent>
        </Dialog>
    )
}