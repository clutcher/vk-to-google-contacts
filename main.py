# -*- coding: utf-8 -*-
import vkontakte

import gdata.data
import gdata.gauth
import gdata.contacts.client
import gdata.contacts.data
import atom

#Google
email = ''
password = ''
groupName = 'VK'
numberOfContacts = '1000'

#VK
#URL for getting token http://oauth.vk.com/authorize?client_id=2859200&scope=friends&response_type=token
tokenVK = ''

#If Ukraine, make it 1
ukraine = 0


def TransformPhone(phone):
    if len(phone) < 5:
        return 0
    phone.replace('-', '')
    phone.replace('(', '')
    phone.replace(')', '')
    phone.replace(' ', '')
    if phone[1:].isdigit():
        if not ukraine:
            return phone
        else:
            if len(phone) == 7:
                return '+38044' + phone
            elif phone[0] == '+':
                return phone
            elif phone[0:3] == '380':
                return '+' + phone
            elif phone[0:2] == '80':
                return '+3' + phone
            elif phone[0] == '0':
                return '+38' + phone
            else:
                return 0
    else:
        return 0


def TransformBirthday(date):
    if len(date) > 5:
        year = date[date.rfind('.') + 1:]
        month = date[date.find('.') + 1:date.rfind('.')]
        if len(month) == 1:
            month = '0' + month
        day = date[0:date.find('.')]
        if len(day) == 1:
            day = '0' + day
        gDate = year + '-' + month + '-' + day
    else:
        month = date[date.rfind('.') + 1:]
        if len(month) == 1:
            month = '0' + month
        day = date[0:date.find('.')]
        if len(day) == 1:
            day = '0' + day
        gDate = '--' + month + '-' + day

    return gDate


def makeStr(data):
    return data.encode('utf-8')


def GetIndex(seq, attribute, value):
    return next(index for (index, d) in enumerate(seq) if d[attribute] == value)


def CheckVkGroup(gd_client):
    feed = gd_client.GetGroups()
    for entry in feed.entry:
        if makeStr(entry.title.text) == groupName:
            return entry.id.text
    return 0


def CreateVkGroup(gd_client):
    new_group = gdata.contacts.data.GroupEntry(title=atom.data.Title(text=groupName))
    created_group = gd_client.CreateGroup(new_group)
    return created_group


def GetAllContacts(gd_client):
    query = gdata.contacts.client.ContactsQuery()
    query.max_results = numberOfContacts
    feed = gd_client.GetContacts(q=query)
    return feed.entry


def downloadPhoto(url, file_name):
    from urllib2 import Request, urlopen

    #Create the request
    req = Request(url)

    # Open the url
    f = urlopen(req)

    # Open our local file for writing
    local_file = open(file_name, "wb")
    #Write to our local file
    local_file.write(f.read())
    local_file.close()


def removeLocalPhoto(file_name):
    from os import remove

    remove(file_name)


def UpdateContact(gd_client, contact, friend, vkGroup):

    #Set the contact's phone numbers.
    if ('mobile_phone' in friend) and (friend['mobile_phone'] != 0):
        contact.phone_number.append(gdata.data.PhoneNumber(text=friend['mobile_phone'],
                                                           rel=gdata.data.WORK_REL, primay='true'))
    if ('home_phone' in friend) and (friend['home_phone'] != 0):
        contact.phone_number.append(gdata.data.PhoneNumber(text=friend['home_phone'],
                                                           rel=gdata.data.HOME_REL))
    if 'bdate' in friend:
        contact.birthday = gdata.contacts.data.Birthday(when=friend['bdate'])

    #Set Group for VK friends
    contact.group_membership_info.append(gdata.contacts.data.GroupMembershipInfo(href=vkGroup))

    #Push changes to Google
    gd_client.Update(contact)

    #Download photo from vk, add to google, remove from local computer
    local_image_filename = friend['photo_big'][friend['photo_big'].rfind('/') + 1:]
    downloadPhoto(friend['photo_big'], local_image_filename)
    gd_client.ChangePhoto(local_image_filename, contact, content_type='image/jpeg')
    removeLocalPhoto(local_image_filename)


def CreateContact(gd_client, friend, vkGroup):

    new_contact = gdata.contacts.data.ContactEntry()
    name = friend['full_name']
    new_contact = gdata.contacts.data.ContactEntry(name=gdata.data.Name(full_name=gdata.data.FullName(text=name)))
    contact = gd_client.CreateContact(new_contact)

    UpdateContact(gd_client, contact, friend, vkGroup)


if __name__ == '__main__':

    #Google authorization
    gd_client = gdata.contacts.client.ContactsClient(source='Export contacts to Google')
    gd_client.ClientLogin(email, password, gd_client.source)

    #Get contacts
    googleContacts = GetAllContacts(gd_client)
    print "Received Google Contacs"

    #VK authorization
    vk = vkontakte.API('2859200', 'Uq9YfuXTq8RUZbrGNnEP')
    vk = vkontakte.API(token=tokenVK)

    #Get list of VK friends
    friends = vk.friends.get(fields="first_name, last_name, bdate, contacts, photo_big", order='name')
    print "Received VK friends"

    #Create group in Google Contacs for VK if not exist
    vkGroup = CheckVkGroup(gd_client)
    if not vkGroup:
        CreateVkGroup(gd_client)
        vkGroup = CheckVkGroup(gd_client)

    #Make list of VK friends more useful
    vkFriendsName = []
    for record in friends:
        record['full_name'] = record['first_name'] + u' ' + record['last_name']

        if 'bdate' in record:
            record['bdate'] = TransformBirthday(record['bdate'])
        if 'home_phone' in record:
            record['home_phone'] = TransformPhone(record['home_phone'])
        if 'mobile_phone' in record:
            record['mobile_phone'] = TransformPhone(record['mobile_phone'])

        del record['first_name']
        del record['last_name']
        del record['uid']
        del record['online']
        vkFriendsName.append(record['full_name'])

    #Update existing contacts
    for contact in googleContacts:
        #Some magics, because of retrieving none existed Google contact
        try:
            makeStr(contact.name.full_name.text)
        except:
            pass
        else:
            if contact.name.full_name.text in vkFriendsName:
                index = GetIndex(friends, 'full_name', contact.name.full_name.text)
                friend = friends[index]
                UpdateContact(gd_client, contact, friend, vkGroup)
                print "Updated: " + makeStr(friend['full_name'])
                vkFriendsName.remove(friend['full_name'])

    #Create new contacts
    for name in vkFriendsName:
        index = GetIndex(friends, 'full_name', name)
        friend = friends[index]
        CreateContact(gd_client, friend, vkGroup)
        print "Created: " + makeStr(friend['full_name'])
