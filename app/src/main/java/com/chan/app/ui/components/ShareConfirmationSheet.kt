package com.chan.app.ui.components

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Login
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.Text
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import com.chan.app.R
import com.chan.app.ui.theme.ChanTheme

/**
 * Modal shown before CHAN imports content shared from another app. Content is
 * imported ONLY when the user taps "Mở trong CHAN".
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ShareConfirmationSheet(
    isImage: Boolean,
    onConfirm: () -> Unit,
    onCancel: () -> Unit,
) {
    val colors = ChanTheme.colors
    val sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)

    ModalBottomSheet(
        onDismissRequest = onCancel,
        sheetState = sheetState,
        shape = RoundedCornerShape(topStart = ChanTheme.dimens.sheetCorner, topEnd = ChanTheme.dimens.sheetCorner),
        containerColor = colors.card,
    ) {
        Column(modifier = Modifier.padding(start = 20.dp, end = 20.dp, bottom = 28.dp)) {
            Eyebrow(text = stringResource(R.string.share_eyebrow), color = colors.brand)
            Spacer(Modifier.height(8.dp))
            Text(
                text = stringResource(R.string.share_title),
                style = ChanTheme.type.sectionTitle,
                color = colors.strongHeading,
            )
            Spacer(Modifier.height(12.dp))
            Text(
                text = if (isImage) {
                    stringResource(R.string.share_explanation_image)
                } else {
                    stringResource(R.string.share_explanation)
                },
                style = ChanTheme.type.body,
                color = colors.bodyText,
            )
            Spacer(Modifier.height(24.dp))
            PrimaryCta(
                text = stringResource(R.string.share_open_in_chan),
                onClick = onConfirm,
                leadingIcon = Icons.AutoMirrored.Filled.Login,
            )
            Spacer(Modifier.height(12.dp))
            SecondaryButton(
                text = stringResource(R.string.action_cancel),
                onClick = onCancel,
            )
        }
    }
}
