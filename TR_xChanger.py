from phBot import *
import QtBind
import struct
import json
import os
import time
from enum import Enum
from datetime import datetime, timedelta

pName = 'TR_xChanger'

character_data = None
exchange_initiator = False
ExchangeStatus = ''
timer = datetime.now()

class ExchangeCode(Enum):
    CLIENT_GAME_PETITION_RESPONSE = 0x3080
    SERVER_GAME_PETITION_REQUEST = 0x3080

    SERVER_EXCHANGE_STARTED = 0x3085
    SERVER_EXCHANGE_CONFIRMED = 0x3086
    SERVER_EXCHANGE_APPROVED = 0x3087
    SERVER_EXCHANGE_CANCELED = 0x3088

    CLIENT_EXCHANGE_START_REQUEST = 0x7081
    CLIENT_EXCHANGE_CONFIRM_REQUEST = 0x7082
    CLIENT_EXCHANGE_APPROVE_REQUEST = 0x7083
    CLIENT_EXCHANGE_CANCEL_REQUEST = 0x7084

    SERVER_EXCHANGE_START_RESPONSE = 0xB081
    SERVER_EXCHANGE_CONFIRM_RESPONSE = 0xB082
    SERVER_EXCHANGE_APPROVE_RESPONSE = 0xB083
    SERVER_EXCHANGE_CANCEL_RESPONSE = 0xB084

gui = QtBind.init(__name__, pName)

_x = 6
_y = 9

QtBind.createLabel(gui, '*  Takasçı listesi (Parti gerekli)', _x, _y)
_y += 20
tbxExchangerName = QtBind.createLineEdit(gui, "", _x, _y, 100, 20)
QtBind.createButton(gui, 'btnAddExchanger_clicked', "    Ekle    ", _x + 101, _y - 2)
_y += 20
lvwExchangers = QtBind.createList(gui, _x, _y, 176, 60)
_y += 60
QtBind.createButton(gui, 'btnRemExchanger_clicked', "     Kaldır     ", _x + 49, _y - 2)
_y += 20 + 10

cbxReplyAccept = QtBind.createCheckBox(gui, 'checkbox_changed', 'Takas isteğini otomatik kabul et', _x, _y)
_y += 20
cbxReplyApprove = QtBind.createCheckBox(gui, 'checkbox_changed', 'Takası otomatik onayla', _x, _y)

_x += 185
_y = 9
cbxAcceptAll = QtBind.createCheckBox(gui, 'checkbox_changed', 'Tüm takas davetlerini kabul et', _x, _y)
_y += 20
cbxAcceptParty = QtBind.createCheckBox(gui, 'checkbox_changed', 'Parti üyelerinden gelen takas davetlerini kabul et', _x, _y)


def get_path():
    return get_config_dir() + pName + "\\"

def get_config():
    return get_path() + character_data['server'] + "_" + character_data['name'] + ".json"

def is_joined():
    global character_data
    character_data = get_character_data()
    if not (character_data and "name" in character_data and character_data["name"]):
        character_data = None
    return character_data

def load_default_config():
    QtBind.setChecked(gui, cbxAcceptAll, False)
    QtBind.setChecked(gui, cbxAcceptParty, False)
    QtBind.setChecked(gui, cbxReplyAccept, True)
    QtBind.setChecked(gui, cbxReplyApprove, True)
    QtBind.clear(gui, lvwExchangers)

def save_configs():
    if is_joined():
        data = {}
        data["AcceptAll"] = QtBind.isChecked(gui, cbxAcceptAll)
        data["AcceptParty"] = QtBind.isChecked(gui, cbxAcceptParty)
        data["ReplyAccept"] = QtBind.isChecked(gui, cbxReplyAccept)
        data["ReplyApprove"] = QtBind.isChecked(gui, cbxReplyApprove)
        data["Exchangers"] = QtBind.getItems(gui, lvwExchangers)

        with open(get_config(), "w") as f:
            f.write(json.dumps(data, indent=4, sort_keys=True))
        log("TR_xChanger: " + pName + " ayarları kaydedildi")

def load_configs():
    load_default_config()
    if is_joined():
        if os.path.exists(get_config()):
            data = {}
            with open(get_config(), "r") as f:
                data = json.load(f)
            if "AcceptAll" in data and data['AcceptAll']:
                QtBind.setChecked(gui, cbxAcceptAll, True)
            if "AcceptParty" in data and data['AcceptParty']:
                QtBind.setChecked(gui, cbxAcceptParty, True)
            if "ReplyAccept" in data and not data['ReplyAccept']:
                QtBind.setChecked(gui, cbxReplyAccept, False)
            if "ReplyApprove" in data and not data['ReplyApprove']:
                QtBind.setChecked(gui, cbxReplyApprove, False)
            if "Exchangers" in data:
                for charName in data["Exchangers"]:
                    QtBind.append(gui, lvwExchangers, charName)

def checkbox_changed(newValue):
    save_configs()

def string_in_list(vString, vList, ModeSensitive=False):
    if not ModeSensitive:
        vString = vString.lower()
    for i in range(len(vList)):
        if not ModeSensitive:
            vList[i] = vList[i].lower()
        if vList[i] == vString:
            return True
    return False

def btnAddExchanger_clicked():
    if character_data:
        player = QtBind.text(gui, tbxExchangerName)
        if player and not string_in_list(player, QtBind.getItems(gui, lvwExchangers)):
            QtBind.append(gui, lvwExchangers, player)
            save_configs()
            QtBind.setText(gui, tbxExchangerName, "")
            log('TR_xChanger: Takasçı eklendi [' + player + ']')

def btnRemExchanger_clicked():
    if character_data:
        selectedItem = QtBind.text(gui, lvwExchangers)
        if selectedItem:
            QtBind.remove(gui, lvwExchangers, selectedItem)
            save_configs()
            log("TR_xChanger: Takasçı kaldırıldı [" + selectedItem + "]")

def get_charname(UniqueID):
    if UniqueID == character_data['player_id']:
        return character_data['name']

    players = get_party()

    if players:
        for key, player in players.items():
            if player['player_id'] == UniqueID:
                return player['name']
    return ""

def Inject_GamePetitionResponse(Accept, Type):
    if Accept:
        p = b'\x01\x01'
    else:
        if Type == 2 or Type == 3:
            p = b'\x02\x0C\x2C'
        else:
            p = b'\x01\x00'
    inject_joymax(ExchangeCode.CLIENT_GAME_PETITION_RESPONSE.value, p, False)

def joined_game():
    load_configs()

def handle_silkroad(opcode, data):
    global exchange_initiator

    if opcode == ExchangeCode.CLIENT_EXCHANGE_START_REQUEST.value:
        global timer
        exchange_initiator = True

        while (datetime.now() - timer < + timedelta(seconds=6)):
            time.sleep(1)

    return True

def handle_joymax(opcode, data):
    if opcode == ExchangeCode.SERVER_GAME_PETITION_REQUEST.value:
        t = data[0]
        if t == 1:
            if QtBind.isChecked(gui, cbxAcceptAll):
                Inject_GamePetitionResponse(True, t)
                return True
            entityID = struct.unpack_from('<I', data, 1)[0]
            charName = get_charname(entityID)

            if QtBind.isChecked(gui, cbxAcceptParty):
                party = get_party()
                if party:
                    for pid, player in party.items():
                        if player['player_id'] == entityID:
                            Inject_GamePetitionResponse(True, t)
                            return True
            if string_in_list(charName, QtBind.getItems(gui, lvwExchangers)):
                Inject_GamePetitionResponse(True, t)
        return True

    global ExchangeStatus
    global exchange_initiator
    global timer

    if opcode == ExchangeCode.SERVER_EXCHANGE_STARTED.value:
        ExchangeStatus = 'STARTED'
    elif opcode == ExchangeCode.SERVER_EXCHANGE_START_RESPONSE.value:
        if data[0] == 1:
            ExchangeStatus = 'STARTED'

    elif opcode == ExchangeCode.SERVER_EXCHANGE_CONFIRMED.value:
        if ExchangeStatus == 'STARTED' and not exchange_initiator:
            if QtBind.isChecked(gui, cbxReplyAccept):
                inject_joymax(ExchangeCode.CLIENT_EXCHANGE_CONFIRM_REQUEST.value, b'', False)

        if ExchangeStatus == 'CONFIRMED' and exchange_initiator:
            if QtBind.isChecked(gui, cbxReplyApprove):
                inject_joymax(ExchangeCode.CLIENT_EXCHANGE_APPROVE_REQUEST.value, b'', False)

    elif opcode == ExchangeCode.SERVER_EXCHANGE_CONFIRM_RESPONSE.value:
        if data[0] == 1:
            ExchangeStatus = 'CONFIRMED'
            if QtBind.isChecked(gui, cbxReplyApprove):
                if not exchange_initiator:
                    inject_joymax(ExchangeCode.CLIENT_EXCHANGE_APPROVE_REQUEST.value, b'', False)

    elif opcode == ExchangeCode.SERVER_EXCHANGE_APPROVE_RESPONSE.value:
        if data[0] == 1:
            ExchangeStatus = 'APPROVED'

    elif opcode == ExchangeCode.SERVER_EXCHANGE_APPROVED.value or opcode == ExchangeCode.SERVER_EXCHANGE_CANCELED.value:
        exchange_initiator = False
        ExchangeStatus = ''
        timer = datetime.now()
    elif opcode == ExchangeCode.SERVER_EXCHANGE_CANCEL_RESPONSE.value:
        if data[0] == 1:
            exchange_initiator = False
            timer = datetime.now()
            ExchangeStatus = ''
    return True

log(f'Eklenti: ' + pName + ' başarıyla yüklendi.')

if os.path.exists(get_path()):
    load_configs()
else:
    os.makedirs(get_path())
    log('TR_xChanger: ' + pName + ' klasörü oluşturuldu')