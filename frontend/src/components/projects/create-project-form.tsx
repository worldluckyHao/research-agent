"use client";

import {
  FormEvent,
  useState,
} from "react";

import {
  ApiError,
} from "@/lib/api";

import {
  createProject,
} from "@/lib/projects-api";

import type {
  Project,
} from "@/types/project";


export function CreateProjectForm({
  onCreated,
}: {
  onCreated: (
    project: Project,
  ) => void;
}) {
  const [
    name,
    setName,
  ] = useState("");

  const [
    description,
    setDescription,
  ] = useState("");

  const [
    error,
    setError,
  ] = useState("");

  const [
    submitting,
    setSubmitting,
  ] = useState(false);


  async function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    setError("");
    setSubmitting(true);

    try {
      const project =
        await createProject({
          name:
            name.trim(),

          description:
            description.trim()
              ? description.trim()
              : null,
        });


      onCreated(
        project,
      );


      setName("");
      setDescription("");

    } catch (err) {
      if (
        err instanceof ApiError
      ) {
        setError(
          err.message,
        );
      } else {
        setError(
          "创建项目失败。",
        );
      }
    } finally {
      setSubmitting(false);
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
        创建科研项目
      </h3>

      <p
        className="
          mt-1
          text-sm
          text-slate-500
        "
      >
        使用 Project 组织论文和后续 AI Research Workflow。
      </p>


      <div
        className="
          mt-5
          space-y-4
        "
      >
        <input
          value={name}

          onChange={
            (event) =>
              setName(
                event.target.value,
              )
          }

          placeholder="项目名称"

          minLength={3}

          maxLength={200}

          required

          className="
            w-full
            rounded-lg
            border
            border-slate-300
            px-4
            py-3
            outline-none
            focus:border-slate-950
          "
        />


        <textarea
          value={description}

          onChange={
            (event) =>
              setDescription(
                event.target.value,
              )
          }

          placeholder="项目描述"

          maxLength={5000}

          rows={5}

          className="
            w-full
            resize-none
            rounded-lg
            border
            border-slate-300
            px-4
            py-3
            outline-none
            focus:border-slate-950
          "
        />


        {error && (
          <div
            className="
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


        <button
          type="submit"

          disabled={
            submitting
          }

          className="
            rounded-lg
            bg-slate-950
            px-5
            py-3
            text-sm
            font-medium
            text-white
            disabled:opacity-60
          "
        >
          {
            submitting
              ? "创建中..."
              : "创建项目"
          }
        </button>
      </div>
    </form>
  );
}