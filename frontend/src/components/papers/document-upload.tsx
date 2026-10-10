"use client";

import {
  ChangeEvent,
  FormEvent,
  useState,
} from "react";

import {
  ApiError,
} from "@/lib/api";

import {
  uploadPaperDocument,
} from "@/lib/documents-api";

import type {
  PaperDocument,
} from "@/types/document";


interface DocumentUploadProps {
  paperId: number;

  onUploaded: (
    document: PaperDocument,
  ) => void;
}


export function DocumentUpload({
  paperId,
  onUploaded,
}: DocumentUploadProps) {
  const [
    file,
    setFile,
  ] = useState<File | null>(
    null,
  );

  const [
    uploading,
    setUploading,
  ] = useState(false);

  const [
    error,
    setError,
  ] = useState("");

  const [
    message,
    setMessage,
  ] = useState("");


  function handleFileChange(
    event:
      ChangeEvent<HTMLInputElement>,
  ) {
    setError("");
    setMessage("");


    const selected =
      event.target.files?.[0];


    if (!selected) {
      setFile(null);

      return;
    }


    const isPdf =
      selected.type ===
        "application/pdf" ||
      selected.name
        .toLowerCase()
        .endsWith(
          ".pdf",
        );


    if (!isPdf) {
      setFile(null);

      setError(
        "请选择 PDF 文件。",
      );

      event.target.value =
        "";

      return;
    }


    setFile(
      selected,
    );
  }


  async function handleSubmit(
    event:
      FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();


    if (!file) {
      setError(
        "请先选择 PDF 文件。",
      );

      return;
    }


    setUploading(true);

    setError("");
    setMessage("");


    try {
      const document =
        await uploadPaperDocument(
          paperId,
          file,
        );


      onUploaded(
        document,
      );


      setMessage(
        "PDF 上传成功。",
      );

      setFile(
        null,
      );

    } catch (err) {
      if (
        err instanceof ApiError
      ) {
        setError(
          err.message,
        );
      } else {
        setError(
          "PDF 上传失败。",
        );
      }
    } finally {
      setUploading(false);
    }
  }


  return (
    <form
      onSubmit={
        handleSubmit
      }

      className="
        rounded-2xl
        border
        border-slate-200
        bg-white
        p-6
        shadow-sm
      "
    >
      <h3
        className="
          text-lg
          font-semibold
          text-slate-950
        "
      >
        Upload PDF
      </h3>


      <p
        className="
          mt-1
          text-sm
          leading-6
          text-slate-500
        "
      >
        上传论文 PDF，
        后续将执行解析、切块和向量化。
      </p>


      <div
        className="
          mt-5
          rounded-xl
          border
          border-dashed
          border-slate-300
          bg-slate-50
          p-5
        "
      >
        <input
          type="file"

          accept=".pdf,application/pdf"

          onChange={
            handleFileChange
          }

          className="
            block
            w-full
            text-sm
            text-slate-600
          "
        />


        {file && (
          <div
            className="
              mt-4
              rounded-lg
              bg-white
              p-3
              text-sm
              text-slate-600
            "
          >
            <p
              className="
                font-medium
                text-slate-950
              "
            >
              {file.name}
            </p>

            <p
              className="
                mt-1
                text-xs
                text-slate-500
              "
            >
              {
                (
                  file.size /
                  1024 /
                  1024
                ).toFixed(
                  2,
                )
              }{" "}
              MB
            </p>
          </div>
        )}
      </div>


      {error && (
        <div
          className="
            mt-4
            rounded-lg
            bg-red-50
            px-4
            py-3
            text-sm
            text-red-700
          "
        >
          {error}
        </div>
      )}


      {message && (
        <div
          className="
            mt-4
            rounded-lg
            bg-emerald-50
            px-4
            py-3
            text-sm
            text-emerald-700
          "
        >
          {message}
        </div>
      )}


      <button
        type="submit"

        disabled={
          uploading ||
          !file
        }

        className="
          mt-5
          rounded-lg
          bg-slate-950
          px-5
          py-3
          text-sm
          font-medium
          text-white
          disabled:cursor-not-allowed
          disabled:opacity-50
        "
      >
        {
          uploading
            ? "Uploading..."
            : "Upload PDF"
        }
      </button>
    </form>
  );
}