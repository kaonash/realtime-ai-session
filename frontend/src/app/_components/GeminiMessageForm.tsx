'use client';

import Image from 'next/image';
import { type FormEvent, type JSX, useEffect, useRef, useState } from 'react';

function UserMessage({ message }: { message: string }) {
  return (
    <div className="flex flex-row px-4 py-8 sm:px-6">
      <Image
        className="mr-2 flex size-24 rounded-full sm:mr-4"
        src="https://dummyimage.com/256x256/354ea1/ffffff&text=G"
        alt="ゲストユーザー"
        width={256}
        height={256}
      />
      <div className="flex max-w-3xl items-center">
        <p>{message}</p>
      </div>
    </div>
  );
}

function AssistantMessage({ message }: { message: string }) {
  return (
    <div className="flex bg-slate-100 px-4 py-8 sm:px-6 dark:bg-slate-900">
      <Image
        className="mr-2 flex size-24 rounded-full sm:mr-4"
        src="/omochi.png"
        alt="おもち"
        width={146}
        height={110}
      />

      <div
        className="flex w-full flex-col items-start lg:flex-row lg:justify-between"
      >
        <p className="max-w-3xl">{message}</p>
        <div
          className="mt-4 flex flex-row justify-start gap-x-2 text-slate-500 lg:mt-0"
        >
        </div>
      </div>
    </div>
  );
}

export function GeminiMessageForm(): JSX.Element {
  const [messages, setMessages] = useState<Array<{ type: 'user' | 'assistant'; content: string }>>([]);
  const [input, setInput] = useState<string>('');
  const [socket, setSocket] = useState<WebSocket | null>(null);
  const audioUrl = useRef<string | null>(null);
  const currentAudio = useRef<HTMLAudioElement | null>(null);
  const [currentAssistantMessageIndex, setCurrentAssistantMessageIndex] = useState(-1);

  const playAudio = async () => {
    console.log('playAudio関数が呼ばれました');
    if (!audioUrl.current) {
      console.log('audioUrlが空のため再生をスキップします');
      return;
    }
    if (currentAudio.current) {
      currentAudio.current.pause();
      currentAudio.current = null;
    }

    const audio = new Audio(audioUrl.current);
    console.log('Audioオブジェクトを作成しました:', audio);
    currentAudio.current = audio;
    audio.addEventListener('ended', () => {
      console.log('音声再生が終了しました');
      currentAudio.current = null;
    });

    try {
      console.log('audio.play()を実行します:', audio);
      await audio.play();
    }
    catch (error) {
      console.error('音声再生エラー', error);
    }
  };

  useEffect(() => {
    // WebSocketサーバーへの接続を確立
    const ws = new WebSocket(String(process.env.NEXT_PUBLIC_GEMINI_REALTIME_API_SERVER_URL));
    setSocket(ws);

    // サーバーからのメッセージを受信
    ws.onmessage = async (event) => {
      console.log('受信したイベントデータ:', event.data);
      try {
        const message = JSON.parse(event.data);
        console.log('JSON.parseの結果:', message);
        console.log('メッセージタイプ:', message.type);
        if (message.type === 'text') {
          setMessages((prevMessages) => {
            const lastMessage = prevMessages[prevMessages.length - 1];
            if (lastMessage?.type === 'assistant') {
              const updatedMessages = [...prevMessages];
              updatedMessages[prevMessages.length - 1] = { ...lastMessage, content: lastMessage.content + message.data };
              return updatedMessages;
            }
            else {
              return [...prevMessages, { type: 'assistant', content: message.data }];
            }
          });
        }
        else if (message.type === 'audio') {
          console.log('audioUrlを設定:', message.data);
          audioUrl.current = message.data;
          playAudio();
        }
      }
      catch (e) {
        console.error('JSONのパースに失敗', e);
        setMessages(prevMessages => [...prevMessages, { type: 'assistant', content: event.data }]);
      }
    };

    // クリーンアップ関数
    return () => {
      ws.close();
    };
  }, []);

  useEffect(() => {
    if (audioUrl.current) {
      playAudio();
    }
  }, [audioUrl.current]);

  const sendMessage = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (currentAudio.current) {
      currentAudio.current.pause();
      currentAudio.current = null;
    }
    audioUrl.current = null;
    setCurrentAssistantMessageIndex(-1);
    if (socket && input) {
      socket.send(input);
      setMessages(prevMessages => [...prevMessages, { type: 'user', content: input }]);
      setInput('');
    }
  };

  return (
    <>
      <div
        className="flex-1 overflow-y-auto bg-slate-300 text-sm leading-6 text-slate-900 shadow-md sm:text-base sm:leading-7 dark:bg-slate-800 dark:text-slate-300"
      >
        {messages.map((message, index) => (
          message.type === 'user'
            ? <UserMessage key={index} message={message.content} />
            : <AssistantMessage key={index} message={message.content} />
        ))}
      </div>

      <form onSubmit={sendMessage}>
        <label htmlFor="chat-input" className="sr-only">Enter prompt</label>
        <div className="flex gap-x-2">
          <input
            id="chat-input"
            type="text"
            value={input}
            className="w-full rounded-lg border border-slate-300 bg-slate-200 p-3 text-sm text-slate-800 shadow-md focus:border-blue-600 focus:outline-none focus:ring-1 focus:ring-blue-600 sm:text-base dark:border-slate-200/10 dark:bg-slate-800 dark:text-slate-200 dark:placeholder:text-slate-400 dark:focus:border-blue-600"
            placeholder="Enter prompt"
            onChange={e => setInput(e.target.value)}
            required
          />
          <button
            type="submit"
            className="rounded-lg border border-transparent bg-blue-600 px-3 py-1 text-slate-200 hover:bg-blue-700 focus:outline-none focus:ring-4 focus:ring-blue-300"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className="size-5"
              viewBox="0 0 24 24"
              strokeWidth="2"
              stroke="currentColor"
              fill="none"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
              <path d="M10 14l11 -11"></path>
              <path
                d="M21 3l-6.5 18a.55 .55 0 0 1 -1 0l-3.5 -7l-7 -3.5a.55 .55 0 0 1 0 -1l18 -6.5"
              >
              </path>
            </svg>
            <span className="sr-only">Enter prompt</span>
          </button>
        </div>
      </form>
    </>
  );
}
