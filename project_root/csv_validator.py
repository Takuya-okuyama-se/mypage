# CSV検証用ユーティリティ
def validate_csv_format(file_content):
    """CSVファイルの形式を検証する関数"""
    import csv
    import io
    
    results = {
        'valid': False,
        'rows': 0,
        'headers': [],
        'sample_data': [],
        'errors': []
    }
    
    try:
        # BOMの確認と除去
        if isinstance(file_content, str) and file_content.startswith('\ufeff'):
            file_content = file_content[1:]
            results['has_bom'] = True
        else:
            results['has_bom'] = False
        
        # CSVファイルを読み込む
        csv_data = io.StringIO(file_content)
        reader = csv.reader(csv_data)
        
        # ヘッダー行を読み取り
        headers = next(reader, None)
        if not headers:
            results['errors'].append("ヘッダー行が空またはCSVフォーマットが不正です")
            return results
        
        results['headers'] = headers
        
        # データ行をサンプル数分だけ読み込み
        sample_count = 5
        sample_data = []
        row_count = 0
        
        for i, row in enumerate(reader, start=2):
            row_count += 1
            if i <= sample_count + 1:
                sample_data.append({
                    'row_num': i,
                    'data': row
                })
        
        results['rows'] = row_count
        results['sample_data'] = sample_data
        
        # CSVは正常に読み込めた
        results['valid'] = True
        return results
    except Exception as e:
        results['errors'].append(f"CSV検証エラー: {str(e)}")
        return results

# インポート時のカラム検出をテストする関数
def test_column_detection(headers):
    """CSVのヘッダーからカラム位置を検出してテストする関数"""
    headers_lower = [h.lower() if h else "" for h in headers]
    
    # 基本的なカラムマッピング（いくつかのパターンに対応）
    question_id_idx = next((i for i, h in enumerate(headers_lower) if 'question' in h and 'id' in h), -1)
    if question_id_idx == -1:
        question_id_idx = next((i for i, h in enumerate(headers_lower) if 'id' in h), 0)
    
    stage_number_idx = next((i for i, h in enumerate(headers_lower) if 'stage' in h), -1)
    if stage_number_idx == -1:
        stage_number_idx = next((i for i, h in enumerate(headers_lower) if 'number' in h), 1)
    
    # 日本語意味 (QuestionText)
    japanese_idx = next((i for i, h in enumerate(headers_lower) if 'question' in h and 'text' in h), -1)
    if japanese_idx == -1:
        japanese_idx = next((i for i, h in enumerate(headers_lower) if 'japanese' in h or 'meaning' in h), -1)
    if japanese_idx == -1:
        japanese_idx = 2  # デフォルトは3列目
    
    # 英単語 (CorrectAnswer)
    english_idx = next((i for i, h in enumerate(headers_lower) if 'correct' in h and 'answer' in h), -1)
    if english_idx == -1:
        english_idx = next((i for i, h in enumerate(headers_lower) if 'english' in h or 'word' in h), -1)
    if english_idx == -1:
        english_idx = 3  # デフォルトは4列目
    
    # 発音情報 (Pronunciation)
    pronunciation_idx = next((i for i, h in enumerate(headers_lower) if 'pronun' in h), -1)
    
    audio_url_idx = next((i for i, h in enumerate(headers_lower) if 'audio' in h or 'url' in h or 'sound' in h), -1)
    notes_idx = next((i for i, h in enumerate(headers_lower) if 'note' in h or 'memo' in h or 'comment' in h), -1)
    
    return {
        'headers': headers,
        'detected_columns': {
            'question_id': {
                'index': question_id_idx,
                'name': headers[question_id_idx] if 0 <= question_id_idx < len(headers) else 'Not Found'
            },
            'stage_number': {
                'index': stage_number_idx,
                'name': headers[stage_number_idx] if 0 <= stage_number_idx < len(headers) else 'Not Found'
            },
            'japanese': {
                'index': japanese_idx,
                'name': headers[japanese_idx] if 0 <= japanese_idx < len(headers) else 'Not Found'
            },
            'english': {
                'index': english_idx,
                'name': headers[english_idx] if 0 <= english_idx < len(headers) else 'Not Found'
            },
            'pronunciation': {
                'index': pronunciation_idx,
                'name': headers[pronunciation_idx] if 0 <= pronunciation_idx < len(headers) else 'Not Found'
            },
            'audio_url': {
                'index': audio_url_idx,
                'name': headers[audio_url_idx] if 0 <= audio_url_idx < len(headers) else 'Not Found'
            },
            'notes': {
                'index': notes_idx,
                'name': headers[notes_idx] if 0 <= notes_idx < len(headers) else 'Not Found'
            }
        }
    }

# エンドポイントで使用するCSV検証関数
def validate_eiken_csv(file_content):
    """エンドポイントで使用するCSV検証関数"""
    results = validate_csv_format(file_content)
    
    if results['valid'] and results['headers']:
        results['column_detection'] = test_column_detection(results['headers'])
    
    return results
