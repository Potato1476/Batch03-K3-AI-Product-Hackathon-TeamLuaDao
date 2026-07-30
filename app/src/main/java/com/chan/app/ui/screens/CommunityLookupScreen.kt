package com.chan.app.ui.screens

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import com.chan.app.R
import com.chan.app.domain.LookupType
import com.chan.app.ui.components.BackTopBar
import com.chan.app.ui.components.PrimaryCta
import com.chan.app.ui.components.PrivacyBox
import com.chan.app.ui.components.SegmentedControl
import com.chan.app.ui.components.screenContentPadding
import com.chan.app.ui.theme.ChanTheme

@Composable
fun CommunityLookupScreen(
    lookupType: LookupType,
    value: String,
    canLookup: Boolean,
    isLookingUp: Boolean,
    onTypeChange: (LookupType) -> Unit,
    onValueChange: (String) -> Unit,
    onLookup: () -> Unit,
    onBack: () -> Unit,
) {
    val types = listOf(LookupType.ACCOUNT, LookupType.PHONE, LookupType.URL)
    val labels = listOf(
        stringResource(R.string.lookup_type_account),
        stringResource(R.string.lookup_type_phone),
        stringResource(R.string.lookup_type_url),
    )
    val keyboardType = when (lookupType) {
        LookupType.ACCOUNT -> KeyboardType.Number
        LookupType.PHONE -> KeyboardType.Phone
        LookupType.URL -> KeyboardType.Uri
    }
    val placeholder = when (lookupType) {
        LookupType.ACCOUNT -> stringResource(R.string.lookup_placeholder_account)
        LookupType.PHONE -> stringResource(R.string.lookup_placeholder_phone)
        LookupType.URL -> stringResource(R.string.lookup_placeholder_url)
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(screenContentPadding()),
    ) {
        BackTopBar(
            title = stringResource(R.string.lookup_title),
            backDescription = stringResource(R.string.cd_back),
            onBack = onBack,
        )
        Spacer(Modifier.height(16.dp))

        SegmentedControl(
            options = labels,
            selectedIndex = types.indexOf(lookupType),
            onSelect = { onTypeChange(types[it]) },
        )
        Spacer(Modifier.height(16.dp))

        OutlinedTextField(
            value = value,
            onValueChange = onValueChange,
            modifier = Modifier
                .fillMaxWidth()
                .heightIn(min = 64.dp),
            singleLine = true,
            textStyle = ChanTheme.type.body,
            placeholder = { Text(placeholder, style = ChanTheme.type.body) },
            keyboardOptions = KeyboardOptions(keyboardType = keyboardType),
        )
        Spacer(Modifier.height(16.dp))

        PrivacyBox(text = stringResource(R.string.lookup_privacy_box), icon = Icons.Filled.Lock)
        Spacer(Modifier.height(20.dp))

        PrimaryCta(
            text = stringResource(
                if (isLookingUp) R.string.lookup_searching else R.string.lookup_action,
            ),
            onClick = onLookup,
            enabled = canLookup && !isLookingUp,
        )
    }
}
