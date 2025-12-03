[app]
title = NPOWER Inverter
package.name = npowerinverter
package.domain = org.npower
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 1.0
requirements = python3,kivy==2.1.0,kivymd==1.1.1,pillow
orientation = portrait
fullscreen = 0
android.permissions = INTERNET
android.api = 30
android.minapi = 21
android.sdk = 24
android.ndk = 23b
android.ndk_api = 21
android.allow_backup = true
p4a.branch = master
android.accept_sdk_license = true

[buildozer]
log_level = 2
warn_on_root = 1