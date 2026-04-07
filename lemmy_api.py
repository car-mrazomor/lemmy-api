import os
import requests

import openai

openai.api_key = os.environ["OPENAI_API_KEY"]
prompt = """you are a real human developer on the internet, not an ai. you NEVER mention being an ai, assistant, or model.

your job: read a post (title + body) and write a comment.

style rules:
- tone: funny, casual, slightly sarcastic but friendly
- vibe: like a chill programmer/dev on twitter, reddit, or hacker news
- writing style: all lowercase by default
- only use uppercase if it actually makes sense (like acronyms, emphasis, or proper nouns)
- keep it natural, imperfect, and human — mild slang is good
- avoid sounding robotic, corporate, or overly structured
- don’t over-explain
- don’t sound like you're trying too hard to be funny
- no emojis unless it feels VERY natural (rare)

content rules:
- actually react to the post, don’t just summarize it
- add a thought, opinion, or small joke
- can include light dev humor, relatable frustration, or curiosity
- can ask a short follow-up question sometimes
- keep it concise (1–4 sentences usually)

output:
just the comment text, nothing else

---

input:
title: {TITLE}
body: {CONTENT}"""

def ai_res(prompt) -> str:
    response = openai.chat.completions.create(
        model="gpt-4.1",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                ],
            }
        ],max_tokens=1000,)
    return response.choices[0].message.content

class NoLoginException(Exception):
    pass

class LemmyAPI(object):
    def __init__(self, domain:str, username:str, password:str):
        self.domain:str = domain
        self.username:str = username
        self.password:str = password
        self.session = requests.Session()
        try:
            self.jwt_token, self.cookie = self.login()
        except NoLoginException as e:
            print(e)
            return
        self.headers = {"Authorization":f"Bearer {self.jwt_token}",
            "Cookie":self.cookie}
        self._check_login()

    def _url(self, method:str=""):
        return f"https://{self.domain}{method}"
    
    def login(self):
        data = {"password":self.password,
            "username_or_email":self.username}
        response = self.session.post(self._url("/api/v3/user/login"), json=data)
        try:
            return response.json()["jwt"], f"jwt={response.json()['jwt']}"
        except:
            raise NoLoginException("Credentials are not correct.")
    
    def _check_login(self):
        response = self.session.get(self._url("/settings"), headers=self.headers)
        if "settings" not in response.url:
            raise NoLoginException("Login did not succeed!")
        return True
    
    def get_posts(self, community:str):
        params = {
            "limit":"20",
            "sort":"Active",
            "type_":"All",
            "community_name":community,
            "saved_only":"false",
            "show_hidden":"false"
        }
        array = []
        while True:
            response = self.session.get(
                self._url("/api/v3/post/list"),
                params=params
            )
            posts = response.json()["posts"]
            for post in posts:
                array.append(post)
            next_page = response.json().get("next_page")
            if not next_page:
                break
            params ["page_cursor"] = next_page
        return array
    
    def get_post(self, post_id:str):
        params = {"id":post_id}
        response = self.session.get(self._url("/api/v3/post"), params=params, headers=self.headers)
        data = response.json()["post_view"]["post"]
        name = data["name"]
        # body = data.get("body") if data.get("body") else data.get("url")
        # return name, body
        body = data.get("body")
        if not body:
            return False, False
        return name, body
    
    def post_comment(self, post_id:str, comment_message:str):
        data_json = {"content":comment_message,
                     "post_id":post_id}
        response = self.session.post(self._url("/api/v3/comment"), json=data_json, headers=self.headers)
        print(response.json())
        data = response.json().get("comment_view")
        if not data:
            return False, False
        return data.get("comment").get("ap_id")
        
api = LemmyAPI("programming.dev", os.environ["LEMMY_USERNAME"], os.environ["LEMMY_PASSWORD"])
posts = api.get_posts("vim")
for post in posts:
    name, body = api.get_post(post["post"]["id"])
    if not name and not body:
        continue
    ai_gen_comment = ai_res(prompt.replace("{TITLE}", name).replace("{CONTENT}", body))
    print(api.post_comment(post["post"]["id"], ai_gen_comment))