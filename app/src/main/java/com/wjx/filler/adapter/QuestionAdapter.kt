package com.wjx.filler.adapter

import android.view.LayoutInflater
import android.view.ViewGroup
import androidx.recyclerview.widget.DiffUtil
import androidx.recyclerview.widget.ListAdapter
import androidx.recyclerview.widget.RecyclerView
import com.wjx.filler.databinding.ItemQuestionBinding
import com.wjx.filler.model.QuestionEntry

/**
 * 题目列表适配器
 */
class QuestionAdapter(
    private val onEdit: (Int) -> Unit,
    private val onDelete: (Int) -> Unit
) : ListAdapter<QuestionEntry, QuestionAdapter.ViewHolder>(DiffCallback()) {

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
        val binding = ItemQuestionBinding.inflate(
            LayoutInflater.from(parent.context),
            parent,
            false
        )
        return ViewHolder(binding)
    }

    override fun onBindViewHolder(holder: ViewHolder, position: Int) {
        holder.bind(getItem(position), position)
    }

    inner class ViewHolder(
        private val binding: ItemQuestionBinding
    ) : RecyclerView.ViewHolder(binding.root) {

        fun bind(entry: QuestionEntry, position: Int) {
            binding.apply {
                questionNumber.text = "第${position + 1}题"
                questionTypeChip.text = entry.questionType.displayName
                questionSummary.text = entry.getSummary()

                btnEdit.setOnClickListener { onEdit(position) }
                btnDelete.setOnClickListener { onDelete(position) }
            }
        }
    }

    class DiffCallback : DiffUtil.ItemCallback<QuestionEntry>() {
        override fun areItemsTheSame(oldItem: QuestionEntry, newItem: QuestionEntry): Boolean {
            return oldItem.questionNum == newItem.questionNum
        }

        override fun areContentsTheSame(oldItem: QuestionEntry, newItem: QuestionEntry): Boolean {
            return oldItem == newItem
        }
    }
}