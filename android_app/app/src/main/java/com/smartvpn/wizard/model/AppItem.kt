package com.smartvpn.wizard.model

import android.graphics.drawable.Drawable

data class AppItem(
    val name: String,
    val packageName: String,
    val icon: Drawable?,
    var isDirect: Boolean = false
)
