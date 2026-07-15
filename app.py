import threading
import time
import requests
import logging
import binascii
import json
import urllib3
import random
import warnings
from datetime import datetime
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from cryptography.hazmat.primitives.ciphers import Cipher as Cp, algorithms as Al, modes as Md
from cryptography.hazmat.backends import default_backend as Bk
from flask import Flask, request, jsonify
from flask_cors import CORS

warnings.filterwarnings("ignore")
urllib3.disable_warnings()

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

K = b"Yg&tc%DEuh6%Zc^8"
IV = b"6oyZDr22E3ychjM%"

dT = bytes.fromhex(
    "1a13323032352d30372d33302031343a31313a3230220966726565206669726528013a07"
    "322e3131342e324234416e64726f6964204f53203133202f204150492d33332028545031"
    "412e3232303632342e3031342f3235303531355631393737294a0848616e6468656c6452"
    "094f72616e676520544e5a0457494649609c1368b80872033438307a1d41524d3634204650"
    "204153494d4420414553207c2032303030207c20388001973c8a010c4d616c692d473532"
    "204d433292013e4f70656e474c20455320332e322076312e72333270312d3031656163302e"
    "32613839336330346361303032366332653638303264626537643761663563359a012b476f"
    "6f676c657c61326365613833342d353732362d346235622d383666322d373130356364386666"
    "353530a2010e3139362e3138372e3132382e3334aa0102656eb201203965373166616266343364"
    "383863303662373966353438313034633766636237ba010134c2010848616e6468656c64ca0115"
    "494e46494e495820496e66696e6978205836383336ea014063363231663264363231343330646163"
    "316137383261306461623634653663383061393734613662633732386366326536623132323464313836"
    "633962376166f00101ca02094f72616e676520544ed2020457494649ca03203161633462383065636630"
    "343738613434323033626638666163363132306635e003dc810ee803daa106f003ef068004e7a506"
    "8804dc810e9004e7a5069804dc810ec80403d2045b2f646174612f6170702f7e7e73444e524632"
    "526357313830465a4d66624d5a636b773d3d2f636f6d2e6474732e66726565666972656d61782d"
    "4a534d4f476d33464e59454271535376587767495a413d3d2f6c69622f61726d3634e00402ea047b"
    "61393862306265333734326162303061313966393737633637633031633266617c2f646174612f6170"
    "702f7e7e73444e524632526357313830465a4d66624d5a636b773d3d2f636f6d2e6474732e66726565"
    "666972656d61782d4a534d4f476d33464e59454271535376587767495a413d3d2f626173652e61706b"
    "f00402f804028a050236349a050a32303139313135363537a80503b205094f70656e474c455333b805"
    "ff7fc00504d20506526164c3a873da05023133e005b9f601ea050b616e64726f69645f6d6178f2055c"
    "4b71734854346230414a3777466c617231594d4b693653517a6732726b3665764f38334f306f59306763"
    "635a626457467a785633483564454f586a47704e3967476956774b7533547a312b716a36326546673074"
    "627537664350553d8206147b226375725f72617465223a5b36302c39305d7d880601900601"
    "9a060134a2060134b20600"
)

def decode_varint(data, pos):
    """فك تشفير varint بدون الاعتماد على protobuf"""
    result = 0
    shift = 0
    while True:
        if pos >= len(data):
            return None, pos
        byte = data[pos]
        pos += 1
        result |= (byte & 0x7F) << shift
        shift += 7
        if not (byte & 0x80):
            break
    return result, pos

def pbD(data):
    """تحليل protobuf يدوياً"""
    i, out = 0, {}
    while i < len(data):
        key, i = decode_varint(data, i)
        if key is None:
            break
        fn, wt = key >> 3, key & 0x7
        if wt == 0:
            v, i = decode_varint(data, i)
            out[str(fn)] = {"t": "int", "v": v}
        elif wt == 2:
            ln, i = decode_varint(data, i)
            if ln is None:
                break
            v = data[i:i+ln]
            i += ln
            try:
                out[str(fn)] = {"t": "str", "v": v.decode()}
            except:
                out[str(fn)] = {"t": "hex", "v": v.hex()}
        elif wt == 1:
            out[str(fn)] = {"t": "64b", "v": data[i:i+8].hex()}
            i += 8
        elif wt == 5:
            out[str(fn)] = {"t": "32b", "v": data[i:i+4].hex()}
            i += 4
        else:
            break
    return out

def padB(d):
    n = 16 - (len(d) % 16)
    return d + bytes([n] * n)

def upd(d):
    p = d[-1]
    return d[:-p] if 1 <= p <= 16 else d

def enc(b):
    c = Cp(Al.AES(K), Md.CBC(IV), backend=Bk())
    e = c.encryptor()
    return e.update(padB(b)) + e.finalize()

def eID(x):
    x = int(x)
    e = []
    while x:
        e.append((x & 0x7F) | (0x80 if x > 0x7F else 0))
        x >>= 7
    return bytes(e).hex()

def ua():
    return random.choice([
        "GarenaMSDK/4.0.19P4(G011A ;Android 9;en;US;)",
        "GarenaMSDK/4.0.18P6(SM-A125F ;Android 11;en;IN;)",
        "GarenaMSDK/4.1.0P3(Redmi 9A ;Android 10;en;ID;)"
    ])

def gTok(u, p):
    """الحصول على access_token و open_id"""
    r = requests.post(
        "https://100067.connect.garena.com/oauth/guest/token/grant",
        headers={
            "Host": "100067.connect.garena.com",
            "User-Agent": ua(),
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "close"
        },
        data={"uid": u, "password": p, "response_type": "token", "client_type": "2", 
              "client_secret": "2ee44819e9b4598845141067b281621874d0d5d7af9d8f7e00c1e54715b7d1e3", 
              "client_id": "100067"},
        verify=False,
        timeout=15
    )
    if r.status_code != 200:
        raise Exception(f"garena {r.status_code}")
    d = r.json()
    return d["access_token"], d["open_id"]

def bLd(at, oid):
    """بناء payload التشفير"""
    x = dT[:]
    x = x.replace(b"2026-04-08 19:23:23", str(datetime.now())[:-7].encode())
    x = x.replace(b"f7b53f72785049be6978604de2815c3cc7c017235f54eab41d8a349c18fb432c", at.encode())
    x = x.replace(b"7f0d30b4c0c9663e83945f6f614d2985", oid.encode())
    return enc(x)

def gJwt(u, p):
    """الحصول على JWT token"""
    try:
        logger.info(f"🔄 جاري الحصول على توكن لـ {u[:6]}...")
        at, oid = gTok(u, p)
        pay = bLd(at, oid)
        r = requests.post(
            "https://loginbp.ggwhitehawk.com/MajorLogin",
            headers={
                "Expect": "100-continue",
                "X-Unity-Version": "2018.4.11f1",
                "X-GA": "v1 1",
                "ReleaseVersion": "OB54",
                "Authorization": "Bearer ",
                "Host": "loginbp.ggwhitehawk.com",
                "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 13; A063)",
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept-Encoding": "gzip"
            },
            data=pay,
            verify=False,
            timeout=20
        )
        if r.status_code != 200:
            raise Exception(f"MajorLogin {r.status_code}")
        d = pbD(r.content)
        tok = d.get("8", {}).get("v", "")
        if not tok:
            raise Exception("no jwt")
        logger.info(f"✅ تم الحصول على توكن لـ {u[:6]}...")
        return tok.strip()
    except Exception as e:
        logger.error(f"❌ فشل الحصول على توكن لـ {u[:6]}...: {e}")
        return None

def encrypt_api(plain_text):
    key = bytes([89, 103, 38, 116, 99, 37, 68, 69, 117, 104, 54, 37, 90, 99, 94, 56])
    iv = bytes([54, 111, 121, 90, 68, 114, 50, 50, 69, 51, 121, 99, 104, 106, 77, 37])
    cipher = AES.new(key, AES.MODE_CBC, iv)
    cipher_text = cipher.encrypt(pad(bytes.fromhex(plain_text), AES.block_size))
    return cipher_text.hex()

def Encrypt_ID(number):
    number = int(number)
    encoded_bytes = []
    while True:
        byte = number & 0x7F
        number >>= 7
        if number:
            byte |= 0x80
        encoded_bytes.append(byte)
        if not number:
            break
    return bytes(encoded_bytes).hex()

l9bi7e_Tok =[
("5446329419", "C4_NAVAROU_2OXKT3GU"),
("5446329415", "C4_NAVAROU_D1BSNPEC"),
("5446329440", "C4_NAVAROU_JEKGKTJ3"),
("5446329399", "C4_NAVAROU_BZXCGIN1"),
("5446329406", "C4_NAVAROU_QQXYGIZD"),
("5446329475", "C4_NAVAROU_D8HCABFN"),
("5446329423", "C4_NAVAROU_1GSNN1XU"),
("5446329424", "C4_NAVAROU_OQ1CGTLP"),
("5446329473", "C4_NAVAROU_YMJDZJCQ"),
("5446329468", "C4_NAVAROU_0VBUWMKK"),
("5446329460", "C4_NAVAROU_UCFMEQQD"),
("5446329413", "C4_NAVAROU_KIARKWGM"),
("5446329466", "C4_NAVAROU_FGICSXOZ"),
("5446329472", "C4_NAVAROU_FQDD1BBW"),
("5446329463", "C4_NAVAROU_IZMUFDFV"),
("5446329459", "C4_NAVAROU_GSUCJVWQ"),
("5446329465", "C4_NAVAROU_UQMOIQPI"),
("5446329464", "C4_NAVAROU_QFNSI07Y"),
("5446329426", "C4_NAVAROU_YVDSR6A7"),
("5446329471", "C4_NAVAROU_SW41XFNZ"),
("5446332791", "C4_NAVAROU_C2X6GL0W"),
("5446334807", "C4_NAVAROU_E86UYNTA"),
("5447488905", "C4_NAVAROU_NHWXEJSV"),
("5447488988", "C4_NAVAROU_VROK98BD"),
("5447488937", "C4_NAVAROU_XRLMQZY9"),
("5447488985", "C4_NAVAROU_JI78IKHP"),
("5447488986", "C4_NAVAROU_LUKPYGJG"),
("5447488907", "C4_NAVAROU_KJAWAIR8"),
("5447488975", "C4_NAVAROU_XLBSM6FO"),
("5447488997", "C4_NAVAROU_PH0EQLS0"),
("5447488980", "C4_NAVAROU_H95M8KJU"),
("5447488901", "C4_NAVAROU_ZLJIOBUB"),
("5447488964", "C4_NAVAROU_HZQU5TTJ"),
("5447489039", "C4_NAVAROU_5KJORXTK"),
("5447488942", "C4_NAVAROU_0GVA9H0M"),
("5447488979", "C4_NAVAROU_7XPU5QCX"),
("5447489012", "C4_NAVAROU_MGSVGZKM"),
("5447488978", "C4_NAVAROU_7VIOPA2H"),
("5447489159", "C4_NAVAROU_5GQXCZRN"),
("5447488984", "C4_NAVAROU_SPWST3YY"),
("5447489162", "C4_NAVAROU_JX32G6VT"),
("5447488921", "C4_NAVAROU_79YIEY4H"),
("5447491121", "C4_NAVAROU_0BBCROOP"),
("5447495114", "C4_NAVAROU_GH3OQMRB"),
]
JWT_ToKeNs = {}
SpAm_RunNiNg = {}
spam_threads = {}

JWT_API_URL = "http://5.180.82.107:4008/GeneRate-Jwt"  # قم بتغيير الرابط إذا كان الـ API مرفوعاً خارجياً

def MaSrY_UpdateJwt():
    """تحديث التوكنات بشكل دوري عن طريق استدعاء الـ API الخارجي"""
    logger.info("🔄 بدء تحديث التوكنات عبر الـ API...")
    while True:
        success_count = 0
        for uId, PaSs in l9bi7e_Tok: 
            if not SpAm_RunNiNg:  # تحقق إضافي لتجنب الاستدعاءات غير الضرورية في حالة الإيقاف الكامل
                pass
            
            try:
                # إرسال طلب إلى API jwt.py لجلب التوكن
                params = {
                    "Uid": uId,
                    "Pw": PaSs
                }
                response = requests.get(JWT_API_URL, params=params, verify=False, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("success") and "BearerAuth" in data:
                        token = data["BearerAuth"]
                        JWT_ToKeNs[uId] = token
                        success_count += 1
                        logger.info(f"✅ تم تحديث توكن الحساب: {uId[:6]}...")
                    else:
                        logger.warning(f"⚠️ الـ API لم يرجع توكن للحساب {uId[:6]}...: {data.get('message')}")
                else:
                    logger.error(f"❌ خطأ من الـ API للحساب {uId[:6]}...: HTTP {response.status_code}")
                
                # تأخير بسيط بين الطلبات لتجنب الضغط على الـ API
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"❌ فشل الاتصال بالـ API للحساب {uId[:6]}...: {e}")
        
        logger.info(f"📊 حصيلة التحديث من الـ API: {success_count}/{len(l9bi7e_Tok)} توكنات جاهزة")
        # التحديث كل 30 دقيقة أو حسب رغبتك (التوكن في ملف jwt مخزن مؤقتاً لـ 7 ساعات)
        time.sleep(1800) 


def MaSrY_SendFriend(target_uid, token, account_uid):
    """إرسال طلب صداقة"""
    try:
        enc_target = Encrypt_ID(target_uid)
        payload = f"08a7c4839f1e10{enc_target}1801"
        enc_payload = encrypt_api(payload)

        headers = {
            "Authorization": f"Bearer {token}",
            "X-Unity-Version": "2018.4.11f1",
            "X-GA": "v1 1",
            "ReleaseVersion": "OB54",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "Dalvik/2.1.0 (Linux; Android 9)"
        }

        response = requests.post(
            "https://clientbp.ggpolarbear.com/RequestAddingFriend",
            headers=headers,
            data=bytes.fromhex(enc_payload),
            timeout=10,
            verify=False
        )

        if response.status_code == 200:
            logger.info(f"✅ نجح: {account_uid[:6]}... -> {target_uid}")
            return response
        else:
            logger.warning(f"❌ فشل {account_uid[:6]}... -> {target_uid}: {response.status_code}")
            return None

    except Exception as e:
        logger.error(f"❌ خطأ: {e}")
        return None

def MaSrY_InfiniteSpam(target_uid, session_id, accounts_list=None):
    """تنفيذ سبام لا نهائي مع معالجة محسنة للتوكنات وتصحيح المتغيرات"""
    global l9bi7e_Tok
    
    success = 0
    failed = 0
    
    # التأكد من استخدام الاسم الصحيح l9bi7e_Tok
    accounts = accounts_list if accounts_list else (l9bi7e_Tok if 'l9bi7e_Tok' in globals() else [])
    
    if not accounts:
        logger.error("❌ لا توجد حسابات متاحة للسبام!")
        return {"success": 0, "failed": 0}

    SpAm_RunNiNg[session_id] = True
    logger.info(f"🚀 بدء سبام على {target_uid} باستخدام {len(accounts)} حساب")
    
    while SpAm_RunNiNg.get(session_id):
        found_any_token = False
        for uid, _ in accounts:
            if not SpAm_RunNiNg.get(session_id):
                break
            
            token = JWT_ToKeNs.get(uid)
            if not token:
                continue
            
            found_any_token = True
            response = MaSrY_SendFriend(target_uid, token, uid)
            
            if response is None:
                failed += 1
            else:
                success += 1
            
            if (success + failed) % 20 == 0:
                update_spam_status(session_id, target_uid, success, failed)
                logger.info(f"📊 تقدم ({session_id[:8]}): نجاح {success} | فشل {failed}")
            
            time.sleep(0.15)
        
        # حماية من استهلاك المعالج إذا لم توجد توكنات
        if not found_any_token:
            time.sleep(5)
            
    logger.info(f"🏁 انتهى سبام {target_uid}: نجاح {success} | فشل {failed}")
    update_spam_status(session_id, target_uid, success, failed)
    SpAm_RunNiNg[session_id] = False
    return {"success": success, "failed": failed}

def update_spam_status(session_id, target_uid, success, failed):
    spam_threads[session_id] = {
        "target_uid": target_uid,
        "success": success,
        "failed": failed,
        "running": SpAm_RunNiNg.get(session_id, False),
        "updated_at": datetime.now().isoformat()
    }

@app.route('/spm', methods=['GET'])
def start_spam():
    try:
        target_uid = request.args.get('uid')
        if not target_uid:
            return jsonify({"status": "error", "message": "الاستخدام: /spm?uid=الهدف"}), 400
        
        session_id = f"{target_uid}_{int(time.time())}"
        
        for sid, info in spam_threads.items():
            if info.get('target_uid') == target_uid and info.get('running'):
                return jsonify({
                    "status": "error",
                    "message": f"يوجد سبام نشط للـ UID {target_uid}",
                    "session_id": sid
                }), 409
        
        thread = threading.Thread(
            target=MaSrY_InfiniteSpam,
            args=(target_uid, session_id, None),
            daemon=True
        )
        thread.start()
        
        spam_threads[session_id] = {
            "target_uid": target_uid,
            "success": 0,
            "failed": 0,
            "running": True,
            "started_at": datetime.now().isoformat()
        }
        
        return jsonify({
            "status": "success",
            "message": f"✅ تم بدء السبام على {target_uid}",
            "session_id": session_id,
            "active_tokens": len(JWT_ToKeNs)
        }), 200
        
    except Exception as e:
        logger.error(f"خطأ: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/stp', methods=['GET'])
def stop_spam():
    try:
        target_uid = request.args.get('uid')
        if not target_uid:
            return jsonify({"status": "error", "message": "الاستخدام: /stp?uid=الهدف"}), 400
        
        stopped_sessions = []
        for sid, info in spam_threads.items():
            if info.get('target_uid') == target_uid and SpAm_RunNiNg.get(sid):
                SpAm_RunNiNg[sid] = False
                stopped_sessions.append(sid)
        
        if stopped_sessions:
            return jsonify({
                "status": "success",
                "message": f"🛑 تم إيقاف {len(stopped_sessions)} جلسة سبام",
                "sessions": stopped_sessions
            }), 200
        
        return jsonify({"status": "error", "message": "❌ لا يوجد سبام نشط لهذا الـ UID"}), 404
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/status', methods=['GET'])
def get_status():
    try:
        target_uid = request.args.get('uid')
        if target_uid:
            sessions = [{"session_id": sid, **info} for sid, info in spam_threads.items() 
                       if info.get('target_uid') == target_uid]
            return jsonify({"status": "success", "data": sessions}), 200
        
        active = {sid: info for sid, info in spam_threads.items() if info.get('running')}
        return jsonify({
            "status": "success",
            "active_sessions_count": len(active),
            "active_tokens": len(JWT_ToKeNs),
            "total_accounts": len(l9bi7e_ToK),
            "data": active
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/tokens', methods=['GET'])
def show_tokens():
    return jsonify({
        "total_accounts": len(l9bi7e_ToK),
        "active_tokens": len(JWT_ToKeNs),
        "status": "جاري التحديث..." if len(JWT_ToKeNs) == 0 else f"{len(JWT_ToKeNs)} توكن نشط"
    }), 200

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        "name": "FreeFire Spam API",
        "status": "running",
        "commands": {
            "start": "/spm?uid=9763926639",
            "stop": "/stp?uid=9763926639", 
            "status": "/status?uid=9763926639",
            "tokens": "/tokens"
        }
    }), 200

if __name__ == "__main__":
    threading.Thread(target=MaSrY_UpdateJwt, daemon=True).start()
    time.sleep(2)
    print("=" * 50)
    print("✅ FreeFire Spam API is Running!")
    print("=" * 50)
    print("\n📌 انتظر 30 ثانية لتحديث التوكنات...")
    print("\nثم استخدم:")
    print(f"  https://friend-spam-l9bi7e.onrender.com/spm?uid=9763926639")
    print(f"  https://friend-spam-l9bi7e.onrender.com/stp?uid=9763926639")
    print("=" * 50)
    
    app.run(host='0.0.0.0', port=7781, debug=False, threaded=True)