"use client";

import { useState, useEffect, use } from "react";
import Image from "next/image";
import Link from "next/link";
import {
  Edit,
  Settings,
  ChevronRight,
  Award,
  BookMarked,
  BookText,
  Users,
  Coffee,
  X,
  User,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Header } from "@/components/layout/Header";
import { useSession } from "@/lib/session";
import { useRouter } from "next/navigation";
import { EditProfileModal } from "@/components/ui/edit/EditProfileModal";
import { DeleteAccountDialog } from "@/components/ui/delete/DeleteAccountDialog";
import { UserSetupModal } from "@/components/ui/userprofile/UserSetupModal";
import CurrentlyReading from "@/components/profiles/CurrentlyReading";
import UserBookClubs from "@/components/profiles/UserBookClubs";
import { toast } from "@/hooks/use-toast";
import UserProfileQuiz from "@/components/profiles/UserProfileQuiz";
import ProfileShelves from '@/components/profiles/ProfileShelves';
import UserReviews from '@/components/profiles/UserReviews';
import { apiFetch } from "@/lib/api";


// Define profile data interface
interface ProfileData {
  id?: string;
  username: string;
  bio?: string;
  zipCode?: string;
  socialLinks?: string;
  need_setup?: boolean;
  profile_pic?: string;
  profile_pic_url?: string;
  stats?: {
    books_read: number;
    average_rating: string;
    favorite_genre: string;
  };
  recently_read?: any[];
  book_clubs?: any[];
  profilePicUrl?: string;
}

// Default profile data
const DEFAULT_PROFILE_DATA: ProfileData = {
  username: "",
  bio: "",
  zipCode: "",
  socialLinks: "",
  need_setup: false,
  stats: {
    books_read: 0,
    average_rating: "N/A",
    favorite_genre: "N/A",
  },
  recently_read: [],
  book_clubs: [],
};

export default function ProfilePage({
  params,
}: {
  params: Promise<{ profileId: string }>;
}) {
  // State variables
  const [profileData, setProfileData] =
    useState<ProfileData>(DEFAULT_PROFILE_DATA);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isCurrentUser, setIsCurrentUser] = useState(false);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [isDeleting, setIsDeleting] = useState<boolean>(false);
  const [showEditModal, setShowEditModal] = useState<boolean>(false);
  const [showSetupModal, setShowSetupModal] = useState<boolean>(false);
  const [showQuizModal, setShowQuizModal] = useState<boolean>(false);

  // Hooks
  const { user, isLoaded, logout } = useSession();
  const router = useRouter();
  const { profileId } = use(params);

  // Load the profile once we know who (if anyone) is signed in.
  useEffect(() => {
    if (!isLoaded) return;
    const ownProfile = !!user && String(user.id) === profileId;
    setIsCurrentUser(ownProfile);
    if (ownProfile) fetchCurrentUserProfile();
    else fetchUserProfile(profileId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [profileId, isLoaded, user?.id]);

  // Handling when user completes the quiz
  const handleQuizComplete = async (
    quizAnswers: Record<string, string | number | boolean>
  ): Promise<boolean> => {
    try {
      // For now, just log the answers and close the modal
      console.log("Quiz answers:", quizAnswers);

      // Later, you'll send these to your backend
      setShowQuizModal(false);

      toast({
        title: "Reading preferences saved!",
        description: "We'll use these to personalize your experience.",
        variant: "default",
      });

      return true;
    } catch (error) {
      console.error("Error saving quiz answers:", error);
      return false;
    }
  };

  // Function to fetch current user's profile
  const fetchCurrentUserProfile = async () => {
    try {
      setLoading(true);
      setError(null);



      const response = await apiFetch("/api/auth/profile/", {
        headers: {
          "Content-Type": "application/json",
        },
      });

      if (!response.ok) {
        throw new Error("Failed to fetch profile data");
      }

      const data = await response.json();
      console.log("Received current user profile data:", data);

      // Check if user needs setup
      if (data.need_setup) {
        setShowSetupModal(true);
      } else if (data.has_completed_quiz === false) {
        setShowQuizModal(true);
      }
      // Format the data to match our ProfileData interface
      setProfileData({
        username: data.username || "",
        bio: data.bio || "",
        zipCode: data.zip_code || "",
        socialLinks: data.social_links || "",
        need_setup: data.need_setup || false,
        profile_pic: data.profile_pic || "",
        profilePicUrl: data.profile_pic || "",
        stats: {
          books_read: 0,
          average_rating: "N/A",
          favorite_genre: "N/A",
        },
        recently_read: [],
        book_clubs: [],
      });

      setLoading(false);
    } catch (err) {
      console.error("Error fetching current user profile:", err);
      setError(
        err instanceof Error ? err.message : "Failed to fetch profile data"
      );
      setLoading(false);
    }
  };

  // Function to fetch another user's profile
  const fetchUserProfile = async (userId: string) => {
    try {
      setLoading(true);
      setError(null);



      // Fetch the public profile of the specified user
      const response = await apiFetch(
        `/api/auth/users/${userId}/`,
        {
          headers: {
            "Content-Type": "application/json",
          },
        }
      );

      if (!response.ok) {
        throw new Error("Failed to fetch profile data");
      }

      const data = await response.json();
      console.log("Received other user profile data:", data);

      // Set the profile data
      setProfileData({
        id: data.id?.toString(),
        username: data.username || "",
        bio: data.bio || "",
        zipCode: data.zip_code || "",
        socialLinks: data.social_links || "",
        profile_pic: data.profile_pic || data.profile_pic_url || "",
        profilePicUrl: data.profile_pic || data.profile_pic_url || "",
        stats: data.stats || {
          books_read: 0,
          average_rating: "N/A",
          favorite_genre: "N/A",
        },
        recently_read: data.recently_read || [],
        book_clubs: data.book_clubs || [],
      });

      setLoading(false);
    } catch (err) {
      console.error("Error fetching user profile:", err);
      setError(
        err instanceof Error ? err.message : "Failed to fetch profile data"
      );
      setLoading(false);
    }
  };

  // Handle profile image URL
  const getProfileImageUrl = (profilePic: string | undefined) => {
    if (!profilePic) return null;

    // Check if it's already an absolute URL
    if (profilePic.startsWith("http")) {
      return profilePic;
    }

    // Make it an absolute URL
    return `${profilePic}`;
  };

  // Handle account deletion
  const handleDeleteAccount = async () => {
    setIsDeleting(true);

    try {


      const response = await apiFetch(
        "/api/auth/user/delete",
        {
          method: "DELETE",
          headers: {
            "Content-Type": "application/json",
          },
        }
      );

      if (response.ok) {
        await logout();
        router.push("/");
      } else {
        console.error("Delete failed:", await response.text());
      }
    } catch (error) {
      console.error("Error deleting account:", error);
    } finally {
      setIsDeleting(false);
    }
  };

  const handleSetupComplete = async (newProfileData : ProfileData): Promise <boolean> => {
    try {
      // Save the profile data first
      const success = await handleSaveProfile(newProfileData);

      if (success) {
        // After successful profile setup, show the quiz
        setShowQuizModal(true);
        return true;
      }
      return false;
    } catch (error) {
      console.error("Error completing setup:", error);
      return false;
    }
  }

  const handleSaveProfile = async (
    newProfileData: ProfileData
  ): Promise<boolean> => {
    try {

      
      const profileUpdateResponse = await apiFetch(
        "/api/auth/user/profile/update/",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            displayName: newProfileData.displayName,
            bio: newProfileData.bio || "",
            zipCode: newProfileData.zipCode || "",
            socialLinks: newProfileData.socialLinks || "",
          }),
        }
      );

      if (!profileUpdateResponse.ok) {
        const errorText = await profileUpdateResponse.text();
        console.error("Profile update failed:", errorText);
        return false;
      }

      
      if (newProfileData.profilePicture instanceof File) {
        console.log(
          "Uploading file:",
          newProfileData.profilePicture.name,
          newProfileData.profilePicture.size
        );
        const imageFormData = new FormData();
        imageFormData.append("profilePicture", newProfileData.profilePicture);

        const imageUploadResponse = await apiFetch(
          "/api/auth/user/profile/update-picture/",
          {
            method: "POST",
            headers: {
            },
            body: imageFormData,
          }
        );

        if (!imageUploadResponse.ok) {
          const errorText = await imageUploadResponse.text();
          console.error("Image upload failed:", errorText);
          return false;
        }

        const result = await imageUploadResponse.json();
        console.log("Upload result:", result);
        if (result.profile_pic_url) {
          setProfileData((prev) => ({
            ...prev,
            profile_pic: result.profile_pic_url,
            profilePicUrl: result.profile_pic_url,
          }));
        }
      }

      if (isCurrentUser) await fetchCurrentUserProfile();

      return true;
    } catch (error) {
      console.error("Error saving profile:", error);
      return false;
    }
  };

  
  // Show loading state
  if (loading) {
    return (
      <div className="min-h-screen bg-amber-50 flex items-center justify-center">
        <div className="text-amber-800 text-xl">Loading profile...</div>
      </div>
    );
  }

  // Show error state
  if (error) {
    return (
      <div className="min-h-screen bg-amber-50 flex items-center justify-center">
        <div className="text-red-600 text-xl">{error}</div>
      </div>
    );
  }

  const profileImageUrl = getProfileImageUrl(
    profileData.profile_pic || profileData.profilePicUrl
  );

  return (
    <div className="flex min-h-screen flex-col bg-amber-50">
      {/* Header */}
      <Header variant="app" />

      <main className="container mx-auto px-4 sm:px-6 py-8 max-w-7xl">
        <div className="grid grid-cols-1 gap-8 md:grid-cols-3 lg:gap-12">
          {/* Left Column - Profile Info */}
          <div className="md:col-span-2">
            <div className="flex flex-col md:flex-row gap-6 items-start mb-8">
              {/* Profile Image */}
              <div className="h-32 w-32 rounded-full overflow-hidden border-4 border-amber-200 bg-amber-100">
                {profileImageUrl ? (
                  <Image
                    src={profileImageUrl}
                    alt="Profile"
                    width={128}
                    height={128}
                    className="h-full w-full object-cover"
                    onError={(e) => {
                      e.currentTarget.style.display = "none";
                    }}
                    unoptimized
                  />
                ) : (
                  <div className="flex items-center justify-center h-full w-full bg-amber-100 text-amber-700">
                    <User className="h-16 w-16" />
                  </div>
                )}
              </div>

              {/* User Info */}
              <div className="flex-1 space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h1 className="text-2xl font-serif font-bold text-amber-900">
                      {profileData.username}
                    </h1>
                  </div>

                  {/* Only show edit buttons for current user */}
                  {isCurrentUser && (
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="icon"
                        className="h-8 w-8 border-amber-300"
                        onClick={() => setShowEditModal(true)}
                      >
                        <Edit className="h-4 w-4 text-amber-800" />
                        <span className="sr-only">Edit Profile</span>
                      </Button>
                      <Button
                        variant="outline"
                        size="icon"
                        className="h-8 w-8 border-amber-300"
                      >
                        <Settings className="h-4 w-4 text-amber-800" />
                        <span className="sr-only">Settings</span>
                      </Button>
                      <Button
                        variant="outline"
                        size="icon"
                        className="h-8 w-8 border-amber-300"
                        onClick={() => setShowDeleteDialog(true)}
                      >
                        <X className="h-4 w-4 text-amber-800" />
                        <span className="sr-only">Delete Account</span>
                      </Button>
                    </div>
                  )}
                </div>

                {/* Bio */}
                <div className="rounded-lg border border-amber-200 bg-amber-50 p-4">
                  <p className="text-amber-800">
                    {profileData.bio || "No bio available."}
                  </p>
                </div>
              </div>
            </div>

            {/* Currently Reading Section */}
            <CurrentlyReading
              userId={profileId === "me" ? undefined : profileId}
              showAddButton={isCurrentUser}
              className="mb-8"
            />

  
          {/*user shelves */}
          <div className="mb-8">
            <h2 className="text-xl font-serif font-bold text-amber-900 mb-4">My Shelves</h2>
            <ProfileShelves 
              userId={profileData.username}
              shelfTypes={["Reading", "Favorites", "Read", "Want to Read", "Owned"]}
            />
          </div>

         {/* Add the new User Reviews section */}
        <UserReviews 
          userId={profileId === "me" ? undefined : profileId} 
          className="mb-8"
        />



            {/* Recent Books / Want to Read - Only show if there's actual data */}
            {profileData.recently_read &&
              profileData.recently_read.length > 0 && (
                <div className="mb-8 rounded-lg border border-amber-200 bg-white p-6">
                  <div className="flex items-center justify-between mb-4">
                    <h2 className="text-xl font-serif font-bold text-amber-900">
                      {isCurrentUser ? "Want to Read" : "Recently Read"}
                    </h2>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-amber-800"
                    >
                      View All <ChevronRight className="ml-1 h-4 w-4" />
                    </Button>
                  </div>

                  <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4">
                    {profileData.recently_read.map((book) => (
                      <div key={book.id} className="space-y-2">
                        <div className="aspect-[2/3] overflow-hidden rounded-md bg-amber-200">
                          <Image
                            src={
                              book.cover_image ||
                              `/placeholder.svg?height=150&width=100&text=Book`
                            }
                            alt={book.title}
                            width={100}
                            height={150}
                            className="h-full w-full object-cover"
                            unoptimized
                          />
                        </div>
                        <div>
                          <Link
                            href={`/book/${book.id}`}
                            className="text-sm font-medium text-amber-900 hover:underline line-clamp-1"
                          >
                            {book.title}
                          </Link>
                          <p className="text-xs text-amber-700 line-clamp-1">
                            {book.author}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
          </div>

          {/* Right Column - Sidebar */}
          <div className="space-y-8">
            {/* Book Clubs */}
            <div className="rounded-lg border border-amber-200 bg-white p-6">
              <h2 className="mb-4 text-xl font-serif font-bold text-amber-900">
                Book Clubs
              </h2>
              <UserBookClubs
                userId={profileId === "me" ? undefined : profileId}
                showAddButton={isCurrentUser}
                limit={5}
              />
            </div>

            {/* Achievement Showcase - Use placeholder for now */}
            <div className="rounded-lg border border-amber-200 bg-white p-6">
              <h2 className="mb-4 text-xl font-serif font-bold text-amber-900">
                Achievement Showcase
              </h2>
              <div className="grid grid-cols-3 gap-4">
                {[1, 2, 3, 4, 5, 6].map((achievement) => (
                  <div
                    key={achievement}
                    className="flex flex-col items-center text-center"
                  >
                    <div className="flex h-14 w-14 items-center justify-center rounded-full bg-amber-100">
                      <Award className="h-8 w-8 text-amber-600" />
                    </div>
                    <span className="mt-2 text-xs text-amber-800 line-clamp-2">
                      {achievement % 2 === 0 ? "Bookworm" : "Speed Reader"}
                    </span>
                  </div>
                ))}
              </div>
              <Button
                variant="ghost"
                size="sm"
                className="mt-4 w-full text-amber-800"
              >
                View All Achievements
              </Button>
            </div>

            {/* Quick Links - Only show for current user */}
            {isCurrentUser && (
              <div className="grid grid-cols-2 gap-4">
                <Link
                  href="/book"
                  className="flex flex-col items-center justify-center rounded-lg border border-amber-200 bg-white p-4 text-center transition-colors hover:bg-amber-100"
                >
                  <BookMarked className="h-8 w-8 text-amber-800" />
                  <span className="mt-2 font-medium text-amber-900">
                    My Books
                  </span>
                </Link>
                <Link
                  href="/journals"
                  className="flex flex-col items-center justify-center rounded-lg border border-amber-200 bg-white p-4 text-center transition-colors hover:bg-amber-100"
                >
                  <BookText className="h-8 w-8 text-amber-800" />
                  <span className="mt-2 font-medium text-amber-900">
                    My Journals
                  </span>
                </Link>
                <Link
                  href="/community"
                  className="flex flex-col items-center justify-center rounded-lg border border-amber-200 bg-white p-4 text-center transition-colors hover:bg-amber-100"
                >
                  <Users className="h-8 w-8 text-amber-800" />
                  <span className="mt-2 font-medium text-amber-900">
                    Community Hub
                  </span>
                </Link>
                <Link
                  href="/club"
                  className="flex flex-col items-center justify-center rounded-lg border border-amber-200 bg-white p-4 text-center transition-colors hover:bg-amber-100"
                >
                  <Coffee className="h-8 w-8 text-amber-800" />
                  <span className="mt-2 font-medium text-amber-900">
                    Book Clubs
                  </span>
                </Link>
              </div>
            )}

            {/* Reading Stats */}
            <div className="rounded-lg border border-amber-200 bg-white p-6">
              <h2 className="mb-4 text-xl font-serif font-bold text-amber-900">
                Reading Stats
              </h2>
              <div className="space-y-4">
                <div className="flex justify-between">
                  <span className="text-amber-800">Books Read:</span>
                  <span className="font-medium text-amber-900">
                    {profileData.stats?.books_read || 0}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-amber-800">Average Rating:</span>
                  <span className="font-medium text-amber-900">
                    {profileData.stats?.average_rating || "N/A"} ★
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-amber-800">Favorite Genre:</span>
                  <span className="font-medium text-amber-900">
                    {profileData.stats?.favorite_genre || "N/A"}
                  </span>
                </div>
              </div>

              {/* Reading Challenge - Only show for current user */}
              {isCurrentUser && (
                <div className="mt-4 rounded-lg bg-amber-100 p-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-amber-800">
                      2025 Reading Challenge
                    </span>
                    <span className="text-sm font-medium text-amber-900">
                      64% Complete
                    </span>
                  </div>
                  <Progress value={64} className="mt-2 h-2 bg-amber-200" />
                </div>
              )}
            </div>
          </div>
        </div>
      </main>

      {isCurrentUser && (
        <>
          <EditProfileModal
            isOpen={showEditModal}
            onClose={() => setShowEditModal(false)}
            onSave={handleSaveProfile}
            initialData={{
              username: profileData.username,
              bio: profileData.bio || "",
              zipCode: profileData.zipCode || "",
              socialLinks: profileData.socialLinks || "",
              profilePicUrl:
                profileData.profile_pic || profileData.profilePicUrl || "",
            }}
          />

          <DeleteAccountDialog
            isOpen={showDeleteDialog}
            onClose={() => setShowDeleteDialog(false)}
            onConfirm={handleDeleteAccount}
            isLoading={isDeleting}
          />

          <UserSetupModal
            isOpen={showSetupModal}
            onClose={() => {
              setShowSetupModal(false);
              if (!profileData.need_setup) {
                setShowQuizModal(true);
              }
            }}
            onSave={handleSetupComplete}
            initialData={{
              username: profileData.username,
              bio: profileData.bio || "",
              zipCode: profileData.zipCode || "",
              socialLinks: profileData.socialLinks || "",
              need_setup: profileData.need_setup || false,
              profilePicUrl:
                profileData.profile_pic || profileData.profilePicUrl || "",
            }}
          />

          <UserProfileQuiz
            isOpen={showQuizModal}
            onComplete={handleQuizComplete}
            onSkip={() => setShowQuizModal(false)}
          />
        </>
      )}
    </div>
  );
}
