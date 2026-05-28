import { useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import * as THREE from 'three'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js'

/**
 * HeroRobot — ربات با IK دست‌ها
 * - سر: pivot در گردن، می‌چرخد به سمت موس
 * - دست: زنجیر shoulder → elbow → wrist → hand
 *   با IK ساده دو-بخشی به سمت موس دست دراز می‌کند
 */
export default function HeroRobot() {
  const mountRef = useRef(null)
  const mouseRef = useRef({ x: 0, y: 0 })

  useEffect(() => {
    const mount = mountRef.current
    if (!mount) return

    const W = mount.clientWidth
    const H = mount.clientHeight

    const scene = new THREE.Scene()
    const camera = new THREE.PerspectiveCamera(35, W / H, 0.1, 100)
    camera.position.set(0, 0.5, 6)
    camera.lookAt(0, 0, 0)

    const renderer = new THREE.WebGLRenderer({
      antialias: true, alpha: true, powerPreference: 'high-performance',
    })
    renderer.setSize(W, H)
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    renderer.shadowMap.enabled = true
    renderer.shadowMap.type = THREE.PCFSoftShadowMap
    renderer.toneMapping = THREE.ACESFilmicToneMapping
    renderer.toneMappingExposure = 1.8
    mount.appendChild(renderer.domElement)

    // ═══ نور قوی ═══
    scene.add(new THREE.AmbientLight(0xffffff, 1.2))
    const keyLight = new THREE.DirectionalLight(0xffffff, 2.5)
    keyLight.position.set(3, 6, 4)
    keyLight.castShadow = true
    keyLight.shadow.mapSize.set(2048, 2048)
    keyLight.shadow.bias = -0.0005
    scene.add(keyLight)

    const fillLight = new THREE.DirectionalLight(0xffffff, 1.4)
    fillLight.position.set(-3, 2, 3)
    scene.add(fillLight)

    const frontLight = new THREE.DirectionalLight(0xffffff, 1.0)
    frontLight.position.set(0, 0, 5)
    scene.add(frontLight)

    const yellowAccent = new THREE.PointLight(0xfbc02d, 2.0, 12)
    yellowAccent.position.set(-3, 1, 3)
    scene.add(yellowAccent)

    const rimLight = new THREE.DirectionalLight(0xfbc02d, 0.8)
    rimLight.position.set(0, 1, -4)
    scene.add(rimLight)

    let robot = null
    const parts = {}  // { headPivot, armL: {shoulder, elbow, wrist}, armR: {...} }

    const loader = new GLTFLoader()
    loader.load(
      '/models/robot.glb',
      (gltf) => {
        robot = gltf.scene

        const box = new THREE.Box3().setFromObject(robot)
        const size = box.getSize(new THREE.Vector3())
        const scale = 3 / size.y
        robot.scale.setScalar(scale)

        const box2 = new THREE.Box3().setFromObject(robot)
        const center2 = box2.getCenter(new THREE.Vector3())
        robot.position.x = -center2.x
        robot.position.y = -center2.y
        robot.position.z = -center2.z

        robot.traverse((obj) => {
          if (obj.isMesh) {
            obj.castShadow = true
            obj.receiveShadow = true
            if (obj.material) {
              obj.material.envMapIntensity = 1.5
              obj.material.needsUpdate = true
            }
          }
        })

        // ─── پیدا کردن mesh ها ───
        const meshes = {}
        const allMeshNames = []
        robot.traverse((obj) => {
          if (!obj.isMesh) return
          allMeshNames.push(obj.name)
          const n = obj.name
          const nLower = n.toLowerCase()
          // case-insensitive matching
          if (!meshes.head && (nLower === 'head' || nLower.includes('head') || nLower.includes('سر'))) meshes.head = obj
          else if (n === 'ArmL_Upper') meshes.armL_upper = obj
          else if (n === 'ArmL_Lower') meshes.armL_lower = obj
          else if (n === 'ArmL_Hand') meshes.armL_hand = obj
          else if (n === 'ArmR_Upper') meshes.armR_upper = obj
          else if (n === 'ArmR_Lower') meshes.armR_lower = obj
          else if (n === 'ArmR_Hand') meshes.armR_hand = obj
          else if (!meshes.body && (nLower === 'body' || nLower.includes('body'))) meshes.body = obj
        })

        console.log('═══ همه mesh های موجود در فایل ═══')
        allMeshNames.forEach(n => console.log(`  • ${n}`))
        console.log('═══ Mesh های شناسایی شده ═══')
        Object.keys(meshes).forEach(k => console.log(`  ${k}: ${meshes[k]?.name}`))
        if (!meshes.head) console.warn('⚠ سر (Head) پیدا نشد! اسم mesh سر را در لیست بالا چک کنید.')

        // ─── ساخت زنجیر برای سر و دست‌ها ───
        if (meshes.head) {
          parts.headPivot = createPivotAtJoint(meshes.head, 'head')
        }

        if (meshes.armL_upper && meshes.armL_lower && meshes.armL_hand) {
          parts.armL = createArmChain(meshes.armL_upper, meshes.armL_lower, meshes.armL_hand, 'left')
        }

        if (meshes.armR_upper && meshes.armR_lower && meshes.armR_hand) {
          parts.armR = createArmChain(meshes.armR_upper, meshes.armR_lower, meshes.armR_hand, 'right')
        }

        scene.add(robot)
      },
      (progress) => {
        if (progress.total > 0) {
          console.log(`Loading: ${((progress.loaded / progress.total) * 100).toFixed(0)}%`)
        }
      },
      (error) => console.error('خطا در لود ربات:', error)
    )

    // سایه و halo
    const shadow = new THREE.Mesh(
      new THREE.CircleGeometry(1.5, 32),
      new THREE.MeshBasicMaterial({ color: 0x000000, transparent: true, opacity: 0.5 })
    )
    shadow.rotation.x = -Math.PI / 2
    shadow.position.y = -2.0
    scene.add(shadow)

    const halo = new THREE.Mesh(
      new THREE.RingGeometry(0.6, 1.8, 64),
      new THREE.MeshBasicMaterial({
        color: 0xfbc02d, transparent: true, opacity: 0.20, side: THREE.DoubleSide,
      })
    )
    halo.rotation.x = -Math.PI / 2
    halo.position.y = -1.99
    scene.add(halo)

    // ── Animation ─────────────────────────────────────────────
    const clock = new THREE.Clock()
    let animId

    // smoothed mouse
    const smoothMouse = { x: 0, y: 0 }
    const SMOOTH = 0.063  // 10% سریع‌تر از قبل (0.0575 → 0.063)
    const clamp = (v, mn, mx) => Math.max(mn, Math.min(mx, v))

    const animate = () => {
      const t = clock.getElapsedTime()
      const m = mouseRef.current

      // smooth کردن موس
      smoothMouse.x += (m.x - smoothMouse.x) * SMOOTH
      smoothMouse.y += (m.y - smoothMouse.y) * SMOOTH

      // clamp موس smoothed به محدوده -0.6 تا 0.6 تا دفرم نشود
      const sm = {
        x: clamp(smoothMouse.x, -0.6, 0.6),
        y: clamp(smoothMouse.y, -0.6, 0.6),
      }

      if (robot) {
        if (!robot.userData.baseY) robot.userData.baseY = robot.position.y
        robot.position.y = robot.userData.baseY + Math.sin(t * 1.2) * 0.03

        robot.rotation.y = sm.x * 0.10  // +30%

        // سر — 30% بیشتر
        if (parts.headPivot) {
          if (!parts.headPivot.userData.orderSet) {
            parts.headPivot.rotation.order = 'YXZ'
            parts.headPivot.userData.initX = parts.headPivot.rotation.x
            parts.headPivot.userData.initY = parts.headPivot.rotation.y
            parts.headPivot.userData.initZ = parts.headPivot.rotation.z
            parts.headPivot.userData.orderSet = true
            console.log('Head pivot initial rotation:',
              parts.headPivot.userData.initX,
              parts.headPivot.userData.initY,
              parts.headPivot.userData.initZ)
          }
          parts.headPivot.rotation.y = parts.headPivot.userData.initY + sm.x * 0.65   // +30%
          parts.headPivot.rotation.x = parts.headPivot.userData.initX + sm.y * 0.78   // +30%
          parts.headPivot.rotation.z = parts.headPivot.userData.initZ
        }

        // ─── دست چپ — همه ضرایب +30% ───
        if (parts.armL) {
          const wobble = Math.sin(t * 1.2) * 0.03

          if (!parts.armL.userData?.orderSet) {
            parts.armL.shoulder.rotation.order = 'YXZ'
            parts.armL.elbow.rotation.order = 'YXZ'
            parts.armL.wrist.rotation.order = 'YXZ'
            parts.armL.userData = { orderSet: true }
          }

          parts.armL.shoulder.rotation.z = sm.x * 0.13 + wobble
          parts.armL.shoulder.rotation.x = -sm.y * 0.16

          parts.armL.elbow.rotation.x = -Math.abs(sm.y) * 0.91 - 0.4 - Math.abs(sm.x) * 0.65
          parts.armL.elbow.rotation.z = sm.x * 0.39

          // مچ بدون چرخش پیش‌فرض — حالت طبیعی
          parts.armL.wrist.rotation.x = sm.y * 0.65
          parts.armL.wrist.rotation.z = sm.x * 0.52
          parts.armL.wrist.rotation.y = sm.x * 0.39
        }

        // ─── دست راست — همه ضرایب +30% ───
        if (parts.armR) {
          const wobble = -Math.sin(t * 1.2) * 0.03

          if (!parts.armR.userData?.orderSet) {
            parts.armR.shoulder.rotation.order = 'YXZ'
            parts.armR.elbow.rotation.order = 'YXZ'
            parts.armR.wrist.rotation.order = 'YXZ'
            parts.armR.userData = { orderSet: true }
          }

          parts.armR.shoulder.rotation.z = sm.x * 0.13 + wobble
          parts.armR.shoulder.rotation.x = -sm.y * 0.16

          parts.armR.elbow.rotation.x = -Math.abs(sm.y) * 0.91 - 0.4 - Math.abs(sm.x) * 0.65
          parts.armR.elbow.rotation.z = sm.x * 0.39

          parts.armR.wrist.rotation.x = sm.y * 0.65
          parts.armR.wrist.rotation.z = sm.x * 0.52
          parts.armR.wrist.rotation.y = sm.x * 0.39
        }
      }

      halo.material.opacity = 0.16 + Math.sin(t * 2) * 0.08
      yellowAccent.intensity = 1.8 + Math.sin(t * 1.8) * 0.4

      renderer.render(scene, camera)
      animId = requestAnimationFrame(animate)
    }
    animate()

    const onMove = (e) => {
      const rect = mount.getBoundingClientRect()
      mouseRef.current.x = ((e.clientX - rect.left) / rect.width) * 2 - 1
      mouseRef.current.y = ((e.clientY - rect.top) / rect.height) * 2 - 1
    }
    window.addEventListener('mousemove', onMove)

    const onResize = () => {
      const w = mount.clientWidth, h = mount.clientHeight
      camera.aspect = w / h
      camera.updateProjectionMatrix()
      renderer.setSize(w, h)
    }
    window.addEventListener('resize', onResize)

    return () => {
      cancelAnimationFrame(animId)
      window.removeEventListener('mousemove', onMove)
      window.removeEventListener('resize', onResize)
      if (renderer.domElement.parentNode === mount) {
        mount.removeChild(renderer.domElement)
      }
      renderer.dispose()
      scene.traverse(o => {
        if (o.geometry) o.geometry.dispose()
        if (o.material) {
          if (Array.isArray(o.material)) o.material.forEach(m => m.dispose())
          else o.material.dispose()
        }
      })
    }
  }, [])

  return (
    <section style={{
      minHeight: '100vh', position: 'relative',
      display: 'flex', alignItems: 'center',
      overflow: 'hidden', background: 'transparent',
    }}>
      <div style={{
        position: 'absolute', right: '15%', top: '50%',
        transform: 'translateY(-50%)',
        width: 600, height: 600, borderRadius: '50%',
        background: 'radial-gradient(circle, rgba(251,192,45,0.18) 0%, rgba(251,192,45,0.06) 35%, transparent 65%)',
        filter: 'blur(50px)', pointerEvents: 'none',
      }}/>

      <div style={{
        position: 'absolute', inset: 0, pointerEvents: 'none',
        backgroundImage:
          'linear-gradient(rgba(255,255,255,0.02) 1px, transparent 1px),' +
          'linear-gradient(90deg, rgba(255,255,255,0.02) 1px, transparent 1px)',
        backgroundSize: '80px 80px',
        maskImage: 'radial-gradient(ellipse at center, black 30%, transparent 80%)',
      }}/>

      <div style={{
        maxWidth: 1280, margin: '0 auto', padding: '0 40px',
        width: '100%', display: 'grid',
        gridTemplateColumns: '1fr 1fr',
        gap: 40, alignItems: 'center', direction: 'rtl',
        position: 'relative', zIndex: 2,
      }}>
        <div>
          <div style={{
            display: 'inline-flex', alignItems: 'center', gap: 8,
            background: 'rgba(251,192,45,0.10)',
            border: '1px solid rgba(251,192,45,0.25)',
            borderRadius: 100, padding: '6px 16px', marginBottom: 28,
          }}>
            <div style={{
              width: 6, height: 6, borderRadius: '50%',
              background: '#fbc02d', animation: 'heroPulse 2s infinite',
              boxShadow: '0 0 10px #fbc02d',
            }}/>
            <span style={{ fontSize: 11, color: '#fbc02d', letterSpacing: '2px' }}>
              DOORBINKAR — بازرگانی تخصصی
            </span>
          </div>

          <h1 style={{
            fontSize: 'clamp(34px,4vw,64px)', fontWeight: 900,
            lineHeight: 1.1, marginBottom: 20, color: '#fff',
          }}>
            قطعات{' '}
            <span style={{
              background: 'linear-gradient(135deg,#fbc02d,#f9a825)',
              WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
              filter: 'drop-shadow(0 0 20px rgba(251,192,45,0.4))',
            }}>دوربین</span>
            <br/>
            <span style={{ fontSize: '0.72em', fontWeight: 400, color: 'rgba(255,255,255,0.55)' }}>
              مداربسته — هوشمند، سریع، اصل
            </span>
          </h1>

          <p style={{
            fontSize: 16, color: 'rgba(255,255,255,0.5)',
            lineHeight: 1.85, marginBottom: 36, maxWidth: 480,
          }}>
            بازرگانی دوربینکار — تأمین تخصصی لنز، برد، سنسور، ISP و تمام قطعات
            دوربین مداربسته. قیمت کارخانه، ضمانت اصالت، تحویل سریع.
          </p>

          <div style={{ display: 'flex', gap: 14, flexWrap: 'wrap' }}>
            <Link to="/products" style={{
              display: 'inline-flex', alignItems: 'center', gap: 10,
              background: 'linear-gradient(135deg,#fbc02d,#f9a825)',
              color: '#000', textDecoration: 'none', borderRadius: 14,
              padding: '16px 32px', fontSize: 15, fontWeight: 700,
              boxShadow: '0 8px 32px rgba(251,192,45,0.4)',
              fontFamily: 'Tahoma',
            }}>
              مشاهده محصولات
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                <path d="M5 12h14M12 5l7 7-7 7" stroke="#000" strokeWidth="2.5" strokeLinecap="round"/>
              </svg>
            </Link>
            <Link to="/partner" style={{
              display: 'inline-flex', alignItems: 'center', gap: 8,
              background: 'rgba(255,255,255,0.06)',
              color: 'rgba(255,255,255,0.85)', textDecoration: 'none',
              border: '1px solid rgba(255,255,255,0.14)',
              borderRadius: 14, padding: '16px 28px', fontSize: 15,
              fontFamily: 'Tahoma', backdropFilter: 'blur(20px)',
            }}>عضویت همکار</Link>
          </div>

          <div style={{
            display: 'flex', gap: 8, flexWrap: 'wrap',
            marginTop: 36, paddingTop: 28,
            borderTop: '1px solid rgba(255,255,255,0.08)',
          }}>
            {['+۱۰۰۰ نوع قطعه','تحویل ۴۸h','ضمانت اصالت','مستقیم از کارخانه'].map(f => (
              <span key={f} style={{
                fontSize: 11, color: 'rgba(255,255,255,0.55)',
                background: 'rgba(255,255,255,0.04)',
                border: '1px solid rgba(255,255,255,0.08)',
                borderRadius: 100, padding: '5px 12px',
                fontFamily: 'Tahoma',
              }}>{f}</span>
            ))}
          </div>
        </div>

        <div
          ref={mountRef}
          style={{
            width: '100%', height: '720px',
            position: 'relative', cursor: 'crosshair',
          }}
        />
      </div>

      <div style={{
        position: 'absolute', bottom: 32, left: '50%',
        transform: 'translateX(-50%)',
        display: 'flex', flexDirection: 'column',
        alignItems: 'center', gap: 6, zIndex: 5,
      }}>
        <div style={{
          width: 1, height: 50,
          background: 'linear-gradient(to bottom, rgba(251,192,45,0.7), transparent)',
          animation: 'scrollLine 1.5s ease-in-out infinite',
        }}/>
        <span style={{
          fontSize: 9, color: 'rgba(255,255,255,0.3)',
          letterSpacing: '3px', fontFamily: 'monospace',
        }}>SCROLL</span>
      </div>

      <style>{`
        @keyframes heroPulse { 0%,100% { opacity: 1; transform: scale(1) } 50% { opacity: 0.4; transform: scale(0.7) } }
        @keyframes scrollLine { 0% { transform: scaleY(0); transform-origin: top } 50% { transform: scaleY(1) } 100% { transform: scaleY(0); transform-origin: bottom } }
      `}</style>
    </section>
  )
}

// ════════════════════════════════════════════════════════════════
// createPivotAtJoint — pivot را در محل مفصل می‌سازد
// ════════════════════════════════════════════════════════════════
function createPivotAtJoint(mesh, type) {
  mesh.updateMatrixWorld(true)
  const box = new THREE.Box3().setFromObject(mesh)
  const size = box.getSize(new THREE.Vector3())

  let jointWorld = new THREE.Vector3()

  if (type === 'head') {
    jointWorld.set(
      (box.min.x + box.max.x) / 2,
      box.min.y + size.y * 0.05,
      (box.min.z + box.max.z) / 2
    )
  }

  const pivot = new THREE.Group()
  const originalParent = mesh.parent
  originalParent.add(pivot)
  originalParent.worldToLocal(jointWorld)
  pivot.position.copy(jointWorld)
  pivot.attach(mesh)
  return pivot
}

// ════════════════════════════════════════════════════════════════
// createArmChain — زنجیر shoulder → elbow → wrist
//
// روش:
// 1) shoulder pivot را در بالای upper بساز
// 2) upper را به shoulder وصل کن
// 3) elbow pivot را در پایین upper (= بالای lower) بساز
//    و آن را child shoulder کن
// 4) lower را به elbow وصل کن
// 5) wrist pivot را در پایین lower (= بالای hand) بساز
//    و آن را child elbow کن
// 6) hand را به wrist وصل کن
//
// نتیجه: زنجیر hierarchical:
//   shoulder → [upper, elbow → [lower, wrist → [hand]]]
// ════════════════════════════════════════════════════════════════
function createArmChain(upper, lower, hand, side) {
  upper.updateMatrixWorld(true)
  lower.updateMatrixWorld(true)
  hand.updateMatrixWorld(true)

  const upperBox = new THREE.Box3().setFromObject(upper)
  const lowerBox = new THREE.Box3().setFromObject(lower)
  const handBox = new THREE.Box3().setFromObject(hand)

  // ── محل مفاصل در world space ──
  // shoulder: بالای بازو
  const shoulderWorld = new THREE.Vector3(
    (upperBox.min.x + upperBox.max.x) / 2,
    upperBox.max.y - (upperBox.max.y - upperBox.min.y) * 0.05,
    (upperBox.min.z + upperBox.max.z) / 2
  )

  // elbow: پایین بازو / بالای ساعد
  // محل: مرز بین upper و lower
  const elbowWorld = new THREE.Vector3(
    (upperBox.min.x + upperBox.max.x + lowerBox.min.x + lowerBox.max.x) / 4,
    Math.min(upperBox.min.y, lowerBox.max.y) + Math.abs(upperBox.min.y - lowerBox.max.y) / 2,
    ((upperBox.min.z + upperBox.max.z) / 2 + (lowerBox.min.z + lowerBox.max.z) / 2) / 2
  )

  // wrist: پایین ساعد / بالای دست
  const wristWorld = new THREE.Vector3(
    (lowerBox.min.x + lowerBox.max.x + handBox.min.x + handBox.max.x) / 4,
    Math.min(lowerBox.min.y, handBox.max.y) + Math.abs(lowerBox.min.y - handBox.max.y) / 2,
    ((lowerBox.min.z + lowerBox.max.z) / 2 + (handBox.min.z + handBox.max.z) / 2) / 2
  )

  const robot = upper.parent  // فرض: همه children robot هستند

  // ── shoulder pivot ──
  const shoulder = new THREE.Group()
  robot.add(shoulder)
  const shoulderLocal = shoulderWorld.clone()
  robot.worldToLocal(shoulderLocal)
  shoulder.position.copy(shoulderLocal)

  // upper را به shoulder منتقل کن (با حفظ موقعیت)
  shoulder.attach(upper)

  // ── elbow pivot ──
  // باید child shoulder باشد
  const elbow = new THREE.Group()
  shoulder.add(elbow)
  const elbowLocal = elbowWorld.clone()
  shoulder.worldToLocal(elbowLocal)
  elbow.position.copy(elbowLocal)

  // lower را به elbow منتقل کن
  elbow.attach(lower)

  // ── wrist pivot ──
  const wrist = new THREE.Group()
  elbow.add(wrist)
  const wristLocal = wristWorld.clone()
  elbow.worldToLocal(wristLocal)
  wrist.position.copy(wristLocal)

  // hand را به wrist منتقل کن
  wrist.attach(hand)

  return { shoulder, elbow, wrist }
}
