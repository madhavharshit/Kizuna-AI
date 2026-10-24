import React, { useEffect, useState } from 'react';
import {
  ActivityIndicator, Alert, Linking, ScrollView, StatusBar, StyleSheet,
  Text, TouchableOpacity, View,
} from 'react-native';
import { SafeAreaProvider, SafeAreaView } from 'react-native-safe-area-context';
import { CameraView, useCameraPermissions } from 'expo-camera';

const API = (process.env.EXPO_PUBLIC_API_URL || 'http://localhost:8000').replace(/\/$/, '');
const AR = (process.env.EXPO_PUBLIC_AR_URL || 'http://localhost:8080/ar/').replace(/\/$/, '') + '/';

function asText(value) {
  if (value === null || value === undefined) return '';
  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') return String(value);
  if (Array.isArray(value)) return value.map(asText).filter(Boolean).join(', ');
  if (typeof value === 'object') {
    for (const key of ['description', 'instruction', 'text', 'message', 'title', 'name', 'label', 'value']) {
      if (value[key] !== undefined && value[key] !== null) {
        const result = asText(value[key]);
        if (result) return result;
      }
    }
  }
  return '';
}
async function get(path) {
  const response = await fetch(API + path);
  const body = await response.json();
  if (!response.ok) throw new Error(body.detail || 'API request failed');
  return body;
}
async function post(path, payload) {
  const response = await fetch(API + path, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
  });
  const body = await response.json();
  if (!response.ok) throw new Error(body.detail || 'API request failed');
  return body;
}

function AppContent() {
  const [procedures, setProcedures] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [selected, setSelected] = useState(null);
  const [step, setStep] = useState(0);
  const [checked, setChecked] = useState([]);
  const [quiz, setQuiz] = useState('');
  const [quizDone, setQuizDone] = useState(false);
  const [scan, setScan] = useState(false);
  const [permission, requestPermission] = useCameraPermissions();

  const load = async () => {
    setLoading(true);
    try { setProcedures(await get('/api/training/procedures')); setError(''); }
    catch (err) { setError(`${err.message} · Check the configured API URL and network connection.`); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);
  const begin = (procedure) => { setSelected(procedure); setStep(0); setChecked([]); setQuiz(''); setQuizDone(false); };
  const markStep = () => setChecked((items) => items.includes(step) ? items : [...items, step]);
  const launchAR = () => {
    const instruction = asText(selected?.steps?.[step]?.instruction) || 'Follow the approved procedure';
    const warning = asText(selected?.warnings?.[0]) || 'Follow site safety requirements';
    const url = `${AR}?title=${encodeURIComponent(asText(selected?.title) || 'Approved training')}`
      + `&step=${encodeURIComponent(instruction)}&warning=${encodeURIComponent(warning)}`;
    Linking.openURL(url).catch(() => Alert.alert('AR unavailable', 'Check the configured AR webpage URL.'));
  };
  const saveProgress = async () => {
    if (!selected) return;
    setSaving(true);
    try {
      await post('/api/training/progress', {
        procedure_id: selected.id,
        trainee_name: 'Demo Trainee',
        completed_steps: checked.length,
        total_steps: selected.steps?.length || 0,
        quiz_score: quizDone && quiz === 'Stop and ask the trainer / follow escalation process' ? 100 : 0,
        completed: checked.length === (selected.steps?.length || 0) && (selected.steps?.length || 0) > 0
          && quizDone && quiz === 'Stop and ask the trainer / follow escalation process',
      });
      Alert.alert('Progress saved', 'Training progress was saved to SkillBridge AR.');
    } catch (err) { Alert.alert('Could not save', err.message); }
    finally { setSaving(false); }
  };
  const openScanner = async () => {
    if (!permission?.granted) {
      const result = await requestPermission();
      if (!result.granted) return;
    }
    setScan(true);
  };

  if (scan) return <SafeAreaView style={styles.root} edges={['top', 'bottom']}>
    <View style={styles.scanHeader}><TouchableOpacity accessibilityRole="button" onPress={() => setScan(false)} style={styles.backButton}><Text style={styles.backText}>‹  Back</Text></TouchableOpacity><Text style={styles.scanTitle}>Scan machine QR</Text><View style={styles.headerSpacer}/></View>
    <View style={styles.cameraWrap}><CameraView style={StyleSheet.absoluteFill} facing="back" barcodeScannerSettings={{ barcodeTypes: ['qr'] }} onBarcodeScanned={({ data }) => { setScan(false); try { const url = new URL(data); if (url.protocol === 'http:' || url.protocol === 'https:') Linking.openURL(data); else Alert.alert('QR detected', data); } catch { Alert.alert('QR detected', data); } }}/><View style={styles.scanFrame}/><Text style={styles.scanHint}>Align the code inside the frame</Text></View>
  </SafeAreaView>;

  return <SafeAreaView style={styles.root} edges={['top', 'left', 'right']}><StatusBar barStyle="dark-content" backgroundColor={colors.paper}/>
    <ScrollView contentContainerStyle={styles.container} keyboardShouldPersistTaps="handled">
      <View style={styles.header}><View style={styles.brandRow}><View style={styles.brandMark}><View/><View/><View/></View><View><Text style={styles.kicker}>INDUSTRIAL KNOWLEDGE</Text><Text style={styles.title}>SkillBridge</Text></View></View><TouchableOpacity accessibilityRole="button" accessibilityLabel="Scan machine QR code" style={styles.scanButton} onPress={openScanner}><Text style={styles.scanIcon}>⌗</Text><Text style={styles.scanButtonText}>Scan QR</Text></TouchableOpacity></View>
      {!selected ? <>
        <View style={styles.intro}><Text style={styles.eyebrow}>TRAINING LIBRARY</Text><Text style={styles.heading}>Learn from verified expertise.</Text><Text style={styles.introText}>Step-by-step guidance from procedures approved by experienced reviewers.</Text></View>
        <View style={styles.stats}><View style={styles.stat}><Text style={styles.statNum}>{loading ? '—' : procedures.length}</Text><Text style={styles.statLabel}>Approved procedures</Text></View><View style={styles.stat}><View style={styles.liveRow}><View style={styles.liveDot}/><Text style={styles.liveText}>SOURCE-BACKED</Text></View><Text style={styles.statLabel}>Expert reviewed guidance</Text></View></View>
        <View style={styles.sectionHead}><View><Text style={styles.sectionTitle}>Procedures</Text><Text style={styles.sectionHint}>Choose a procedure to begin training</Text></View><TouchableOpacity accessibilityRole="button" onPress={load} style={styles.refresh}><Text style={styles.refreshText}>Refresh</Text></TouchableOpacity></View>
        {error ? <View style={styles.error}><Text style={styles.errorTitle}>Could not load training</Text><Text style={styles.errorText}>{error}</Text><TouchableOpacity accessibilityRole="button" onPress={load} style={styles.retry}><Text style={styles.retryText}>Try again</Text></TouchableOpacity></View> : null}
        {loading ? <View style={styles.loading}><ActivityIndicator color={colors.teal} size="small"/><Text style={styles.loadingText}>Loading approved procedures…</Text></View> : procedures.length ? procedures.map((procedure) => <TouchableOpacity accessibilityRole="button" accessibilityLabel={`Open ${asText(procedure.title)}`} style={styles.listCard} key={procedure.id} onPress={() => begin(procedure)}>
          <View style={styles.listIcon}><Text style={styles.listIconText}>SOP</Text></View><View style={styles.listBody}><View style={styles.listMeta}><Text style={styles.approvedTag}>APPROVED</Text><Text style={styles.sopId}>SOP {procedure.id}</Text></View><Text style={styles.listTitle}>{asText(procedure.title)}</Text><Text style={styles.meta}>{Array.isArray(procedure.steps) ? procedure.steps.length : 0} guided steps</Text>{asText(procedure.description) ? <Text style={styles.body} numberOfLines={2}>{asText(procedure.description)}</Text> : null}</View><Text style={styles.chevron}>›</Text>
        </TouchableOpacity>) : !error ? <View style={styles.empty}><View style={styles.emptyGlyph}>✓</View><Text style={styles.emptyTitle}>No published procedures yet</Text><Text style={styles.body}>Once a source is reviewed and approved in the dashboard, its training steps will appear here.</Text></View> : null}
        <View style={styles.footer}><Text style={styles.footerBrand}>SKILLBRIDGE AR</Text><Text style={styles.footerText}>Use current site procedures and safety requirements.</Text></View>
      </> : <>
        <TouchableOpacity accessibilityRole="button" onPress={() => setSelected(null)} style={styles.backButton}><Text style={styles.backText}>‹  Training library</Text></TouchableOpacity>
        <View style={styles.trainingHeader}><View style={styles.listMeta}><Text style={styles.approvedTag}>EXPERT-APPROVED</Text><Text style={styles.sopId}>SOP {selected.id}</Text></View><Text style={styles.procTitle}>{asText(selected.title)}</Text><Text style={styles.body}>{asText(selected.description)}</Text></View>
        <View style={styles.progressCard}><View style={styles.progressTop}><Text style={styles.progressLabel}>YOUR PROGRESS</Text><Text style={styles.progressValue}>{checked.length} / {selected.steps?.length || 0} steps</Text></View><View style={styles.progressTrack}><View style={[styles.progressFill, { width: `${selected.steps?.length ? checked.length / selected.steps.length * 100 : 0}%` }]}/></View></View>
        {Array.isArray(selected.tools) && selected.tools.length > 0 && <View style={styles.infoCard}><Text style={styles.cardLabel}>REQUIRED TOOLS</Text><Text style={styles.toolText}>{selected.tools.map(asText).filter(Boolean).join('  ·  ')}</Text></View>}
        {Array.isArray(selected.warnings) && selected.warnings.length > 0 && <View style={styles.warningCard}><Text style={styles.warningHeading}>SAFETY NOTES</Text>{selected.warnings.map((warning, index) => <Text style={styles.warningText} key={index}>•  {asText(warning)}</Text>)}<Text style={styles.warningFoot}>If conditions differ, pause and check with an expert.</Text></View>}
        <View style={styles.stepCard}><View style={styles.stepHead}><Text style={styles.stepCount}>STEP {selected.steps?.length ? step + 1 : 0} / {selected.steps?.length || 0}</Text><Text style={styles.stepPosition}>{selected.steps?.length ? `${Math.round((step + 1) / selected.steps.length * 100)}%` : ''}</Text></View><View style={styles.stepDivider}/><Text style={styles.stepText}>{asText(selected.steps?.[step]?.instruction) || 'No step available. Return to the review studio for procedure updates.'}</Text>{selected.steps?.[step]?.source_ref || selected.steps?.[step]?.timestamp ? <Text style={styles.meta}>Source: {asText(selected.steps?.[step]?.source_ref) || 'Procedure reference'}{selected.steps?.[step]?.timestamp ? ` · ${asText(selected.steps[step].timestamp)}` : ''}</Text> : null}<TouchableOpacity accessibilityRole="checkbox" accessibilityState={{ checked: checked.includes(step) }} style={styles.checkRow} onPress={markStep}><View style={[styles.checkbox, checked.includes(step) && styles.checkboxOn]}><Text style={styles.checkboxTick}>{checked.includes(step) ? '✓' : ''}</Text></View><Text style={styles.checkText}>I have reviewed this step</Text></TouchableOpacity></View>
        <View style={styles.stepButtons}><TouchableOpacity accessibilityRole="button" disabled={step === 0} style={[styles.secondary, step === 0 && styles.disabled]} onPress={() => setStep(step - 1)}><Text style={styles.secondaryText}>Previous</Text></TouchableOpacity><TouchableOpacity accessibilityRole="button" disabled={step >= (selected.steps?.length || 0) - 1} style={[styles.primary, step >= (selected.steps?.length || 0) - 1 && styles.disabled]} onPress={() => setStep(step + 1)}><Text style={styles.primaryText}>Next step  →</Text></TouchableOpacity></View>
        <TouchableOpacity accessibilityRole="button" style={styles.arButton} onPress={launchAR}><View style={styles.arIcon}><Text style={styles.arIconText}>◎</Text></View><View style={styles.arCopy}><Text style={styles.arTitle}>Open camera AR guidance</Text><Text style={styles.arHint}>View this instruction in the configured experience</Text></View><Text style={styles.arArrow}>↗</Text></TouchableOpacity>
        <View style={styles.quizCard}><Text style={styles.cardLabel}>KNOWLEDGE CHECK</Text><Text style={styles.quizQuestion}>If an instruction is unclear or conditions differ, what should you do?</Text>{['Guess the next step', 'Stop and ask the trainer / follow escalation process', 'Skip the instruction'].map((option) => <TouchableOpacity accessibilityRole="radio" accessibilityState={{ selected: quiz === option }} key={option} style={[styles.option, quiz === option && styles.optionSelected]} onPress={() => { setQuiz(option); setQuizDone(false); }}><View style={styles.radio}>{quiz === option ? <View style={styles.radioDot}/> : null}</View><Text style={styles.optionText}>{option}</Text></TouchableOpacity>)}{quizDone ? <View style={quiz.startsWith('Stop') ? styles.correct : styles.incorrect}><Text style={styles.feedbackText}>{quiz.startsWith('Stop') ? 'Correct. Follow the site escalation process.' : 'Review the procedure and consult an expert when uncertain.'}</Text></View> : null}<TouchableOpacity accessibilityRole="button" disabled={!quiz} style={[styles.checkAnswer, !quiz && styles.disabled]} onPress={() => setQuizDone(true)}><Text style={styles.checkAnswerText}>Check answer</Text></TouchableOpacity></View>
        <TouchableOpacity accessibilityRole="button" disabled={saving || !selected.steps?.length} style={[styles.saveButton, (saving || !selected.steps?.length) && styles.disabled]} onPress={saveProgress}>{saving ? <ActivityIndicator color="#fff"/> : <Text style={styles.primaryText}>Save training progress</Text>}</TouchableOpacity>
      </>}
    </ScrollView>
  </SafeAreaView>;
}

const colors = { paper: '#f4f6f8', ink: '#202c3b', muted: '#798698', teal: '#247d78', line: '#e4e9ee' };
const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.paper }, container: { paddingHorizontal: 18, paddingTop: 8, paddingBottom: 34 },
  header: { minHeight: 56, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 19 }, brandRow: { flexDirection: 'row', alignItems: 'center', gap: 9 }, brandMark: { width: 30, height: 30, borderWidth: 1, borderColor: '#bed2cf', borderRadius: 7, alignItems: 'flex-end', justifyContent: 'center', flexDirection: 'row', gap: 3, padding: 6 },
  kicker: { fontSize: 8, letterSpacing: 1.1, fontWeight: '700', color: '#81909d' }, title: { fontSize: 17, fontWeight: '800', color: '#182b3d', marginTop: 2 }, scanButton: { minHeight: 42, borderRadius: 6, paddingHorizontal: 11, flexDirection: 'row', alignItems: 'center', gap: 6, backgroundColor: '#e8f2f1', borderWidth: 1, borderColor: '#dceae8' }, scanIcon: { fontSize: 17, color: '#347d77' }, scanButtonText: { fontSize: 10, fontWeight: '700', color: '#286c67' },
  intro: { paddingVertical: 16, borderTopWidth: 1, borderTopColor: colors.line, borderBottomWidth: 1, borderBottomColor: colors.line }, eyebrow: { color: '#54827c', letterSpacing: 1.1, fontSize: 8, fontWeight: '800' }, heading: { fontSize: 21, lineHeight: 27, color: '#1d3043', fontWeight: '800', marginTop: 8, letterSpacing: -0.3 }, introText: { color: '#748392', fontSize: 11, lineHeight: 17, marginTop: 6 },
  stats: { flexDirection: 'row', gap: 9, marginVertical: 13 }, stat: { flex: 1, minHeight: 75, justifyContent: 'center', backgroundColor: '#fff', borderWidth: 1, borderColor: colors.line, borderRadius: 6, paddingHorizontal: 12, paddingVertical: 9 }, statNum: { fontSize: 21, fontWeight: '800', color: '#203448' }, statLabel: { fontSize: 9, lineHeight: 13, color: '#798795', marginTop: 4 }, liveRow: { flexDirection: 'row', alignItems: 'center', gap: 6 }, liveDot: { width: 6, height: 6, borderRadius: 3, backgroundColor: '#669a7c' }, liveText: { fontSize: 8, letterSpacing: 0.45, fontWeight: '800', color: '#588168' },
  sectionHead: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginTop: 8, marginBottom: 9 }, sectionTitle: { fontSize: 14, fontWeight: '800', color: '#26384a' }, sectionHint: { fontSize: 9, color: '#87929e', marginTop: 3 }, refresh: { minHeight: 38, justifyContent: 'center', paddingHorizontal: 9 }, refreshText: { fontSize: 10, fontWeight: '700', color: '#377b75' },
  listCard: { backgroundColor: '#fff', borderWidth: 1, borderColor: colors.line, borderRadius: 6, padding: 12, marginBottom: 8, flexDirection: 'row', gap: 10, alignItems: 'center' }, listIcon: { width: 38, height: 38, borderRadius: 5, backgroundColor: '#f0f5f4', alignItems: 'center', justifyContent: 'center' }, listIconText: { fontSize: 9, letterSpacing: 0.3, fontWeight: '900', color: '#437d77' }, listBody: { flex: 1, minWidth: 0 }, listMeta: { flexDirection: 'row', alignItems: 'center', gap: 7 }, approvedTag: { fontSize: 7, fontWeight: '800', letterSpacing: 0.35, color: '#4c7c5c', backgroundColor: '#edf6ef', paddingHorizontal: 5, paddingVertical: 3, overflow: 'hidden', borderRadius: 3 }, sopId: { fontSize: 8, color: '#909ba5' }, listTitle: { fontSize: 12, lineHeight: 17, fontWeight: '800', color: '#2c3f53', marginTop: 6 }, meta: { fontSize: 9, lineHeight: 14, color: '#82909c', marginTop: 4 }, body: { fontSize: 10, lineHeight: 16, color: '#71808f', marginTop: 5 }, chevron: { fontSize: 24, color: '#7da6a0', paddingLeft: 3 },
  loading: { minHeight: 105, backgroundColor: '#fff', borderWidth: 1, borderColor: colors.line, borderRadius: 6, alignItems: 'center', justifyContent: 'center', gap: 8 }, loadingText: { fontSize: 10, color: '#8995a1' }, empty: { padding: 20, backgroundColor: '#fff', borderWidth: 1, borderColor: colors.line, borderRadius: 6, alignItems: 'center' }, emptyGlyph: { width: 30, height: 30, borderRadius: 15, backgroundColor: '#eff5f3', textAlign: 'center', textAlignVertical: 'center', color: '#56877a', fontWeight: '800', overflow: 'hidden', paddingTop: 6 }, emptyTitle: { fontSize: 12, fontWeight: '800', color: '#34475a', marginTop: 9 }, footer: { borderTopWidth: 1, borderTopColor: colors.line, marginTop: 21, paddingTop: 12 }, footerBrand: { fontSize: 8, letterSpacing: 1, fontWeight: '800', color: '#81909d' }, footerText: { fontSize: 8, color: '#9aa3ac', marginTop: 4 },
  backButton: { minHeight: 42, justifyContent: 'center', alignSelf: 'flex-start', paddingRight: 14 }, backText: { color: '#347b75', fontSize: 11, fontWeight: '700' }, trainingHeader: { backgroundColor: '#fff', borderWidth: 1, borderColor: colors.line, borderRadius: 6, padding: 14, marginBottom: 9 }, procTitle: { color: '#203448', fontSize: 18, lineHeight: 24, fontWeight: '800', marginTop: 10 }, progressCard: { borderWidth: 1, borderColor: colors.line, backgroundColor: '#fff', padding: 12, borderRadius: 6, marginBottom: 9 }, progressTop: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }, progressLabel: { fontSize: 8, letterSpacing: 0.7, color: '#7e8c99', fontWeight: '800' }, progressValue: { fontSize: 9, color: '#567e78', fontWeight: '700' }, progressTrack: { height: 4, backgroundColor: '#edf1f1', borderRadius: 3, overflow: 'hidden', marginTop: 9 }, progressFill: { height: 4, borderRadius: 3, backgroundColor: colors.teal },
  infoCard: { backgroundColor: '#fff', borderWidth: 1, borderColor: colors.line, borderRadius: 6, padding: 12, marginBottom: 8 }, cardLabel: { color: '#798795', letterSpacing: 0.65, fontSize: 8, fontWeight: '800' }, toolText: { fontSize: 10, lineHeight: 16, color: '#596b7d', marginTop: 7 }, warningCard: { backgroundColor: '#fffaf1', borderWidth: 1, borderColor: '#eee3cb', borderRadius: 6, padding: 12, marginBottom: 9 }, warningHeading: { fontSize: 8, letterSpacing: 0.7, fontWeight: '900', color: '#97743d', marginBottom: 6 }, warningText: { color: '#775f37', fontSize: 10, lineHeight: 16, marginTop: 3 }, warningFoot: { color: '#9a875f', fontSize: 8, lineHeight: 13, borderTopWidth: 1, borderTopColor: '#eee6d6', paddingTop: 8, marginTop: 7 },
  stepCard: { backgroundColor: '#fff', borderWidth: 1, borderColor: '#dfe7e9', borderRadius: 7, padding: 15, marginTop: 2 }, stepHead: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }, stepCount: { fontSize: 9, letterSpacing: 0.7, fontWeight: '900', color: '#367d77' }, stepPosition: { fontSize: 8, color: '#8c999f' }, stepDivider: { height: 1, backgroundColor: '#edf0f2', marginTop: 11 }, stepText: { fontSize: 16, lineHeight: 24, fontWeight: '700', color: '#273c51', marginTop: 13 }, checkRow: { minHeight: 46, flexDirection: 'row', alignItems: 'center', gap: 9, marginTop: 12, borderTopWidth: 1, borderTopColor: '#edf0f2', paddingTop: 9 }, checkbox: { width: 21, height: 21, borderWidth: 1, borderColor: '#b8c4cb', borderRadius: 4, alignItems: 'center', justifyContent: 'center' }, checkboxOn: { backgroundColor: colors.teal, borderColor: colors.teal }, checkboxTick: { color: '#fff', fontSize: 13, fontWeight: '900' }, checkText: { fontSize: 10, color: '#5d6d7d' }, stepButtons: { flexDirection: 'row', gap: 8, marginTop: 9 }, primary: { flex: 1, minHeight: 46, backgroundColor: colors.teal, paddingHorizontal: 12, borderRadius: 6, alignItems: 'center', justifyContent: 'center' }, primaryText: { color: '#fff', fontWeight: '800', fontSize: 10 }, secondary: { flex: 1, minHeight: 46, borderWidth: 1, borderColor: '#dbe2e6', paddingHorizontal: 12, borderRadius: 6, alignItems: 'center', justifyContent: 'center', backgroundColor: '#fff' }, secondaryText: { color: '#42566a', fontWeight: '800', fontSize: 10 }, disabled: { opacity: 0.45 },
  arButton: { minHeight: 61, flexDirection: 'row', alignItems: 'center', gap: 10, padding: 10, marginTop: 9, backgroundColor: '#192e40', borderRadius: 6 }, arIcon: { width: 34, height: 34, alignItems: 'center', justifyContent: 'center', borderRadius: 5, backgroundColor: '#294758' }, arIconText: { fontSize: 20, color: '#acd0c7' }, arCopy: { flex: 1 }, arTitle: { fontSize: 10, color: '#f2f6f6', fontWeight: '800' }, arHint: { fontSize: 8, lineHeight: 12, color: '#a8b8c0', marginTop: 3 }, arArrow: { fontSize: 15, color: '#b5cec8', paddingHorizontal: 4 },
  quizCard: { backgroundColor: '#fff', borderWidth: 1, borderColor: colors.line, borderRadius: 6, padding: 13, marginTop: 11 }, quizQuestion: { fontSize: 11, lineHeight: 17, fontWeight: '600', color: '#415367', marginTop: 7, marginBottom: 7 }, option: { minHeight: 45, flexDirection: 'row', alignItems: 'center', gap: 9, borderWidth: 1, borderColor: '#e5eaed', paddingHorizontal: 10, borderRadius: 5, marginTop: 6 }, optionSelected: { borderColor: '#8fb8b2', backgroundColor: '#f3f8f7' }, radio: { width: 16, height: 16, borderRadius: 8, borderWidth: 1, borderColor: '#9caab5', alignItems: 'center', justifyContent: 'center' }, radioDot: { width: 8, height: 8, borderRadius: 4, backgroundColor: colors.teal }, optionText: { flex: 1, fontSize: 10, lineHeight: 15, color: '#536578' }, checkAnswer: { minHeight: 42, alignItems: 'center', justifyContent: 'center', borderWidth: 1, borderColor: '#dbe3e6', borderRadius: 5, marginTop: 9 }, checkAnswerText: { color: '#3e6870', fontWeight: '700', fontSize: 10 }, correct: { padding: 9, backgroundColor: '#eff7f0', borderRadius: 4, marginTop: 8 }, incorrect: { padding: 9, backgroundColor: '#fbf4e9', borderRadius: 4, marginTop: 8 }, feedbackText: { fontSize: 9, lineHeight: 14, color: '#59735e' }, saveButton: { minHeight: 48, borderRadius: 6, backgroundColor: '#247d78', alignItems: 'center', justifyContent: 'center', marginTop: 9 },
  error: { backgroundColor: '#fff3f2', borderWidth: 1, borderColor: '#efd8d5', borderRadius: 6, padding: 12, marginBottom: 10 }, errorTitle: { color: '#8d4741', fontSize: 11, fontWeight: '800' }, errorText: { color: '#975c56', fontSize: 9, lineHeight: 15, marginTop: 5 }, retry: { minHeight: 39, justifyContent: 'center', alignSelf: 'flex-start', paddingHorizontal: 4 }, retryText: { color: '#397c76', fontSize: 10, fontWeight: '800' },
  scanHeader: { minHeight: 52, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: 17 }, scanTitle: { color: '#24384b', fontSize: 12, fontWeight: '800' }, headerSpacer: { width: 44 }, cameraWrap: { flex: 1, margin: 15, borderRadius: 9, overflow: 'hidden', backgroundColor: '#0d1c2e', justifyContent: 'center', alignItems: 'center' }, scanFrame: { width: 236, height: 236, borderWidth: 2, borderColor: '#8ec7b9', borderRadius: 15 }, scanHint: { position: 'absolute', bottom: 28, color: '#fff', fontSize: 11, fontWeight: '700' },
});

export default function App() { return <SafeAreaProvider><AppContent/></SafeAreaProvider>; }
