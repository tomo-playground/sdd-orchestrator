"use client";

type Props = {
  text: string;
};

export default function UserBubble({ text }: Props) {
  return (
    <div className="flex justify-end">
      <div className="max-w-[80%] rounded-2xl rounded-br-sm bg-blue-600 px-4 py-2.5 text-sm whitespace-pre-wrap text-white">
        {text}
      </div>
    </div>
  );
}
