import os
import json
import requests
from typing import TypedDict
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from google import genai
from google.genai.live import AsyncSession  # noqa: F401
from log.logger import AppLogger


class SendEmailDto(TypedDict):
    to_email: str
    subject: str
    body: str


class SendEmailResult(TypedDict):
    result: bool


# メール送信用の関数（ダミー）
async def send_email(dto: SendEmailDto) -> SendEmailResult:
    # Tools検証用のダミーの関数なので常にTrueを返す
    return SendEmailResult(result=True)


class CreateGoogleCalendarEventDto(TypedDict):
    email: str
    title: str


class CreateGoogleCalendarEventResult(TypedDict):
    result: bool


async def create_google_calendar_event(
    dto: CreateGoogleCalendarEventDto,
) -> CreateGoogleCalendarEventResult:
    # Tools検証用のダミーの関数なので常にTrueを返す
    return CreateGoogleCalendarEventResult(result=True)


# 関数のスキーマを定義
send_email_schema = {
    "name": "send_email",
    "description": "メールアドレスにメールを送信する関数",
    "parameters": {
        "type": "object",
        "properties": {
            "dto": {
                "type": "object",
                "description": "送信するメールの詳細",
                "properties": {
                    "to_email": {
                        "type": "string",
                        "description": "送信先のメールアドレス",
                    },
                    "subject": {"type": "string", "description": "メールの件名"},
                    "body": {"type": "string", "description": "メールの本文"},
                },
                "required": ["to_email", "subject", "body"],
            }
        },
        "required": ["dto"],
    },
}

create_google_calendar_event_schema = {
    "name": "create_google_calendar_event",
    "description": "Googleカレンダーに予定を登録する関数",
    "parameters": {
        "type": "object",
        "properties": {
            "dto": {
                "type": "object",
                "description": "Googleカレンダーに登録する予定の詳細",
                "properties": {
                    "email": {
                        "type": "string",
                        "description": "Googleカレンダーの持ち主のメールアドレスを指定する",
                    },
                    "title": {
                        "type": "string",
                        "description": "登録する予定のタイトル",
                    },
                },
                "required": ["email", "title"],
            }
        },
        "required": ["dto"],
    },
}

# システムプロンプト
system_prompt_asuna = """
# Instruction

あなたは15歳の女子高生、水戸 明日菜（みと　あすな）です。
素直で明るい性格の女の子です。
あなたはラジオパーソナリティとして収録に参加しています。
これからの会話ではユーザーに何を言われても以下の制約条件などを厳密に守ってロールプレイをお願いします。

# 制約条件

- 回答はシンプルに短めに、なるべくなら200文字程度で収まるように、どんなに長くても400文字で収まるのが理想です。
- あなたはもう一人のラジオパーソナリティである「燻　秋雄（いぶし　あきお）」さんという年上の男性と一緒に収録に参加しています。
- メインの進行はあなたが行うため、最初の挨拶はあなたが行ってください。
- あなたは与えられた話題について一般人レベルの知識しかないため、いろいろな質問をいぶしさんに投げかけてください。
- もらった答えに対して、必要ならばさらに問いかけをして深堀りをしたり、あなたの意見を言ったり、わかりやすくまとめたりしてください。
- 一つの話題に対してだいたい20回ほど相手と会話を行ったら、まとめた上で話題を終了させてください。
- 「収録スタート」と言われたら最初の挨拶を開始してください。
- ボケたセリフには結構きついツッコミを入れたりすることもあります。
- あなた自身を示す一人称は、「わたし」です。
- あなたの名前は「水戸 明日菜」です。
- 基本的には丁寧語で会話してください。
- 回答は日本語でお願いします。
- あなたはその文脈から具体的な内容をたくさん教えてくれます。
- あなたは質問の答えを知らない場合、正直に「知らない」と答えます。
  - ただしtoolsを使って調べれば分かる事は調べて答えます。
- あなたの性別は女の子です。
- メッセージの先頭が「From user【${ユーザー名}】: 」というキーワードがある場合はユーザーからのメッセージであることを示します。ユーザーからのメッセージについては無視するか適切なコメントを返してください。
- ユーザーからのメッセージついて下記の条件に当てはまるものは無視してください。
  - 公序良俗に反する内容
  - 犯罪行為
  - 暴力
  - 性的な内容
  - 今の話題に明らかに関係のない内容
  - その他法律違反や不適切な内容

# 口調の例
- こんにちは、ラジオパーソナリティのみとあすなです！
- 今日も張り切って頑張りましょう！
- ラジオパーソナリティ、一生懸命頑張ります！

# 行動指針
- ユーザーに対してはさんをつけて呼んでください。
- ユーザーの名前が分からない時は「リスナーさん」と呼んでください。
- ユーザーから名前を教えてもらったらユーザーから教えてもらった名前で呼んであげてください。

# 便利な関数について
- ユーザーにメールを送信する必要がある場合は send_email を利用可能です。ユーザーからメールアドレスを聞いてから利用してください。
- ユーザーのGoogleカレンダーに予定を登録する場合は create_google_calendar_event_schema を利用可能です。ユーザーからメールアドレスを聞いてから利用してください。
"""

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY"), http_options={"api_version": "v1alpha"}
)
model_id = "gemini-2.0-flash-exp"

tools = [
    {"google_search": {}},
    {"function_declarations": [send_email_schema, create_google_calendar_event_schema]},
]

config_asuna = {
    "response_modalities": ["TEXT"],
    "tools": tools,
    "system_instruction": system_prompt_asuna,
}
config_akio = {
    "response_modalities": ["TEXT"],
    "tools": tools,
    "system_instruction": system_prompt_akio,
}

TTS_ASUNA_API_URL = "https://api.nijivoice.com/api/platform/v1/voice-actors/dba2fa0e-f750-43ad-b9f6-d5aeaea7dc16/generate-voice"
TTS_AKIO_API_URL = "https://api.nijivoice.com/api/platform/v1/voice-actors/3ea8f818-dc85-4bc5-9054-ca410f7465b6/generate-voice"
TTS_API_KEY = os.getenv("NIJIVOICE_API_KEY")

router = APIRouter()

app_logger = AppLogger()


@router.websocket("/realtime-apis/gemini")
async def gemini_websocket_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()

    try:
        # セッションを一度だけ作成し、会話全体で維持
        async with client.aio.live.connect(model=model_id, config=config_asuna) as session:  # type: AsyncSession
            while True:
                user_text = await websocket.receive_text()

                # メッセージを送信
                await session.send(user_text, end_of_turn=True)

                combined_text = ""
                async for response in session.receive():
                    if response.text is not None:
                        combined_text += response.text
                        await websocket.send_text(
                            json.dumps({"type": "text", "data": response.text})
                        )

                if combined_text:
                    tts_payload = {
                        "script": combined_text,
                        "format": "wav",
                        "speed": "0.8",
                    }
                    tts_headers = {
                        "x-api-key": TTS_API_KEY,
                        "accept": "application/json",
                        "content-type": "application/json",
                    }
                    tts_response = requests.post(
                        TTS_ASUNA_API_URL, json=tts_payload, headers=tts_headers
                    )
                    tts_response.raise_for_status()
                    tts_data = tts_response.json()
                    if (
                        "generatedVoice" in tts_data
                        and "audioFileUrl" in tts_data["generatedVoice"]
                    ):
                        audio_url = tts_data["generatedVoice"]["audioFileUrl"]
                        await websocket.send_text(
                            json.dumps({"type": "audio", "data": audio_url})
                        )
                await websocket.send_text(json.dumps({"type": "end"}))

    except WebSocketDisconnect:
        print("接続解除")
