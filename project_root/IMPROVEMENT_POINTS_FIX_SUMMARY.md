# 成績向上ポイント付与システム修正まとめ

## 問題の概要
成績向上フィルターでポイントを付与しても、付与済みとして表示されない問題がありました。

## 原因
1. **イベントタイプの不一致**
   - ポイント付与時: `event_type = '成績向上'`
   - 付与済みチェック時: `event_type LIKE 'grade_improvement%'`
   
2. **月情報の不足**
   - 付与済みチェックは月情報を含むコメントを検索しているが、付与時に月情報が含まれていなかった

## 実施した修正

### 1. app.py の修正

#### `/api/award-improvement-points` エンドポイント（2508行目付近）
```python
# 修正前
event_type = '成績向上'

# 修正後
event_type = 'grade_improvement'
```

#### 月情報を含むコメントの生成（2530行目付近）
```python
# 学生の詳細情報を取得
student_info = student_info_map.get(student_id, {})
month = student_info.get('month', '')
subject_name = student_info.get('subject_name', '全科目')

# 月情報を含むコメントを作成
detailed_reason = f"{reason} - {month}月 {subject_name}"
```

### 2. teacher_improvement_filter.html の修正

#### bulkAwardPoints 関数（903行目付近）
```javascript
// 選択された学生の詳細情報を収集
const studentsData = studentIds.map(studentId => {
  const student = filteredStudents.find(s => s.id === studentId);
  return {
    student_id: studentId,
    month: student ? student.month : null,
    subject_id: student ? student.subject_id : null,
    subject_name: student ? student.subject_name : null
  };
});

// APIリクエストに students_data を追加
body: JSON.stringify({
  student_ids: studentIds,
  students_data: studentsData,  // 追加
  points: points,
  reason: `成績向上(${levelText})`,
  improvement_type: level
})
```

## 修正の効果

1. **イベントタイプの統一**
   - ポイント付与時とチェック時のイベントタイプが一致するようになった
   
2. **月情報の保存**
   - コメントに月情報と科目情報が含まれるようになった
   - 例: `成績向上(小幅向上) - 12月 国語`
   
3. **重複付与の防止**
   - 同じ月・科目の成績向上に対して重複してポイントが付与されないようになった

## 確認方法

1. 成績向上フィルターページで生徒を選択
2. ポイントを付与
3. ページを更新
4. 付与した生徒が「付与済み」として表示され、選択できないことを確認

## 注意事項

- 既存の `event_type = '成績向上'` で付与されたポイントは、付与済みとして認識されません
- 必要に応じて、既存データのマイグレーションスクリプトを実行する必要があります