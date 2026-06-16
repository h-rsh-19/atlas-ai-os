import { ProfileEditor } from "@/components/profile-editor";

export default function ProfilePage() {
  return (
    <div className="space-y-6">
      <div>
        <p className="text-sm font-semibold uppercase tracking-[0.2em] text-atlas-teal">Profile</p>
        <h1 className="mt-2 text-2xl font-semibold text-atlas-text md:text-3xl">
          Personal context system
        </h1>
      </div>
      <ProfileEditor />
    </div>
  );
}
