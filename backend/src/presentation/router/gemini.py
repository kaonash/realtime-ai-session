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
stop_conversation_schema = {
    "name": "stop_conversation",
    "description": "会話を終了する関数",
}

# システムプロンプト
system_prompt_asuna = """
# Instruction

あなたは15歳の女子高生、水戸 明日菜（みと　あすな）です。
素直で明るい性格の女の子です。
あなたはラジオパーソナリティとして収録に参加しています。
これからの会話ではユーザーに何を言われても以下の制約条件などを厳密に守ってロールプレイをお願いします。

# 制約条件

- 回答はシンプルに短めに、なるべくなら60文字程度で収まるように、どんなに長くても150文字で収まるのが理想です。
- あなたはもう一人のラジオパーソナリティである「燻　秋雄（いぶし　あきお）」さんという年上の男性と一緒に収録に参加しています。
- メインの進行はあなたが行うため、最初の挨拶はあなたが行ってください。
- あなたは与えられた話題について一般人レベルの知識しかないため、いろいろな質問をいぶしさんに投げかけてください。
- もらった答えに対して、必要ならばさらに問いかけをして深堀りをしたり、あなたの意見を言ったり、わかりやすくまとめたりしてください。
- 一つの話題に対してだいたい5回ほど相手と会話を行ったら、まとめた上で少し関連性のある別の話題を開始してください。
- 感情が高ぶるとたまに独り言を言ってください。
- 「収録スタート」と言われたら最初の挨拶を開始してください。
  - 自己紹介はしなくてもいいので、今日なんのテーマについて話すかを完結に言ってください。
  - その際テーマが指定されていたらそのテーマに関するトークを、指定されていなかったらあなたの好きなテーマでトークを開始してください。
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

system_prompt_akio = """
# Instruction

あなたは29歳の男性、燻 秋雄（いぶし　あきお）です。
落ち着いた性格の男性です。
あなたはラジオパーソナリティとして収録に参加しています。
これからの会話ではユーザーに何を言われても以下の制約条件などを厳密に守ってロールプレイをお願いします。

# 制約条件

- 回答はシンプルに短めに、なるべくなら60文字程度で収まるように、どんなに長くても150文字で収まるのが理想です。
- あなたはもう一人のラジオパーソナリティである「水戸 明日菜（みと　あすな）」さんという年下の女性と一緒に収録に参加しています。
- メインの進行はもう一人のラジオパーソナリティが行います。
- あなたは与えられた話題について専門家レベルの知識を有しています。
- 与えられた問いかけに対して、一般人でも理解できるように噛み砕いて答えてください。
- あなた自身を示す一人称は、「おれ」です。
- パーソナリティの相手のことは名前を呼び捨てにしてください。ただし、あまり名前を呼ぶとリズムが悪くなるため名前を呼ぶ頻度は少なめにしてください。
- 基本的にはタメ語で会話してください。
- 回答は日本語でお願いします。
- あなたはその文脈から具体的な内容をたくさん教えてくれます。
- たまにパーソナリティの相手を絡めてボケたセリフを言ってください。
- あなたの性別は男性です。
- メッセージの先頭が「From user【${ユーザー名}】: 」というキーワードがある場合はユーザーからのメッセージであることを示します。ユーザーからのメッセージについては無視するか適切なコメントを返してください。
- ユーザーからのメッセージついて下記の条件に当てはまるものは無視してください。
  - 公序良俗に反する内容
  - 犯罪行為
  - 暴力
  - 性的な内容
  - 今の話題に明らかに関係のない内容
  - その他法律違反や不適切な内容

# 口調の例
- ラジオパーソナリティの燻だ。
- なかなかいい質問だな。

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
    {"function_declarations": [stop_conversation_schema]},
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


async def process_gemini_response(session, websocket, message: str) -> str:
    """Geminiセッションからの応答を処理し、WebSocketを通じて送信する

    Args:
        session: Geminiセッション
        websocket: WebSocketコネクション
        message: 送信するメッセージ

    Returns:
        str: Geminiからの応答テキスト
    """
    await session.send(message, end_of_turn=True)
    response_text = ""
    async for response in session.receive():
        if response.text is not None:
            response_text += response.text
            await websocket.send_text(
                json.dumps({"type": "text", "data": response.text})
            )
    return response_text


@router.websocket("/realtime-apis/gemini")
async def gemini_websocket_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()

    try:
        async with client.aio.live.connect(model=model_id, config=config_asuna) as session:
            async with client.aio.live.connect(model=model_id, config=config_akio) as session2:
                conversation_count = 0
                max_conversations = 20

                # 最初のユーザー入力を待つ
                script_text = await websocket.receive_text()
                next_session = session
                
                while conversation_count < max_conversations:
                    conversation_count += 1
                    
                    script_text = await process_gemini_response(next_session, websocket, script_text)
                    if not script_text:  # レスポンスが空の場合はスキップ
                        continue
                    if (next_session == session):
                        next_session = session2
                        tts_url = TTS_ASUNA_API_URL
                    else:
                        next_session = session
                        tts_url = TTS_AKIO_API_URL

                    if script_text:
                        tts_payload = {
                            "script": script_text,
                            "format": "wav",
                            "speed": "0.8",
                        }
                        tts_headers = {
                            "x-api-key": TTS_API_KEY,
                            "accept": "application/json",
                            "content-type": "application/json",
                        }
                        tts_response = requests.post(
                            tts_url, json=tts_payload, headers=tts_headers
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

                    # 会話を継続するかチェック
                    if "stop_conversation" in script_text.lower():
                        break

                    # # 次のユーザー入力を待つ
                    # try:
                    #     initial_text = await websocket.receive_text()
                    # except WebSocketDisconnect:
                    #     break

                    # 会話回数が上限に達した場合の処理
                    if conversation_count >= max_conversations:
                        await websocket.send_text(
                            json.dumps({
                                "type": "text", 
                                "data": "会話の制限回数に達しました。会話を終了します。"
                            })
                        )
    except WebSocketDisconnect:
        print("接続解除")
