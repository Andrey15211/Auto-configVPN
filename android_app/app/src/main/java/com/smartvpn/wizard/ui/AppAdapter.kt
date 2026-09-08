package com.smartvpn.wizard.ui

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.ImageView
import android.widget.TextView
import androidx.recyclerview.widget.RecyclerView
import com.google.android.material.checkbox.MaterialCheckBox
import com.smartvpn.wizard.R
import com.smartvpn.wizard.model.AppItem

class AppAdapter(
    private var allApps: List<AppItem>
) : RecyclerView.Adapter<AppAdapter.AppViewHolder>() {

    private var filteredApps: List<AppItem> = allApps

    fun updateData(newApps: List<AppItem>) {
        this.allApps = newApps
        this.filteredApps = newApps
        notifyDataSetChanged()
    }

    fun filter(query: String) {
        val q = query.trim().lowercase()
        filteredApps = if (q.isEmpty()) {
            allApps
        } else {
            allApps.filter {
                it.name.lowercase().contains(q) || it.packageName.lowercase().contains(q)
            }
        }
        notifyDataSetChanged()
    }

    fun getSelectedPackages(): List<String> {
        return allApps.filter { it.isDirect }.map { it.packageName }
    }

    fun resetToDefault(defaultPackages: Set<String>) {
        allApps.forEach { app ->
            app.isDirect = defaultPackages.contains(app.packageName)
        }
        notifyDataSetChanged()
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): AppViewHolder {
        val view = LayoutInflater.from(parent.context).inflate(R.layout.item_app, parent, false)
        return AppViewHolder(view)
    }

    override fun onBindViewHolder(holder: AppViewHolder, position: Int) {
        val app = filteredApps[position]
        holder.bind(app)
    }

    override fun getItemCount(): Int = filteredApps.size

    inner class AppViewHolder(itemView: View) : RecyclerView.ViewHolder(itemView) {
        private val ivIcon: ImageView = itemView.findViewById(R.id.ivAppIcon)
        private val tvName: TextView = itemView.findViewById(R.id.tvAppName)
        private val tvPackage: TextView = itemView.findViewById(R.id.tvPackageName)
        private val cbDirect: MaterialCheckBox = itemView.findViewById(R.id.cbDirect)

        fun bind(app: AppItem) {
            tvName.text = app.name
            tvPackage.text = app.packageName
            ivIcon.setImageDrawable(app.icon)

            // Remove listener before setting checked state to avoid recursion
            cbDirect.setOnCheckedChangeListener(null)
            cbDirect.isChecked = app.isDirect

            cbDirect.setOnCheckedChangeListener { _, isChecked ->
                app.isDirect = isChecked
            }

            itemView.setOnClickListener {
                cbDirect.isChecked = !cbDirect.isChecked
            }
        }
    }
}
