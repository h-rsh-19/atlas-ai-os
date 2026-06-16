import { ResumeUploader } from "@/components/resume-uploader";

export default function ResumePage() {
  return (
    <div className="space-y-6">
      <div>
        <p className="text-sm font-semibold uppercase tracking-[0.2em] text-atlas-teal">Resume</p>
        <h1 className="mt-2 text-2xl font-semibold text-atlas-text md:text-3xl">
          Resume intelligence
        </h1>
      </div>
      <ResumeUploader />
    </div>
  );
}
