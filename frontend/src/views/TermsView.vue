<script setup>
import LegalLayout from '../components/LegalLayout.vue'
</script>

<template>
  <LegalLayout title="Términos y condiciones" subtitle="Versión 1.0 · Última actualización: octubre de 2026">
    <article class="legal-doc">
      <h2>1. Aceptación de los términos</h2>
      <p>
        Al crear una cuenta en DAVENT declarás que leíste, comprendiste y aceptaste estos Términos y
        condiciones. Tu aceptación queda registrada con fecha y versión en tu perfil. Si no estás de
        acuerdo con alguna parte, no uses la plataforma.
      </p>

      <h2>2. El servicio</h2>
      <p>
        DAVENT es una plataforma que permite a comercios gestionar catálogos de productos tecnológicos,
        suscripciones y cobros en línea. Actuamos como intermediario tecnológico: el contenido de cada
        catálogo lo publica y controla exclusivamente el comercio titular de la cuenta.
      </p>

      <h2>3. Tu cuenta</h2>
      <ul>
        <li>Sos responsable de la veracidad de los datos que cargás al registrarte (identidad, condición fiscal y datos de contacto).</li>
        <li>Sos responsable de todo lo que ocurra dentro de tu cuenta. Mantené tu contraseña segura y avisanos si detectás un acceso no autorizado.</li>
        <li>La cuenta es personal e intransferible: no podés cederla ni revender el acceso a terceros.</li>
      </ul>

      <h2>4. Contenido del usuario y propiedad intelectual</h2>
      <p>
        Todo texto, imagen, logotipo, fotografía de producto, marca o descripción que subas a tu catálogo
        es <strong>tu responsabilidad exclusiva</strong>. Al publicar contenido en DAVENT declarás que:
      </p>
      <ul>
        <li>Sos titular de los derechos sobre ese contenido o contás con autorización escrita del titular.</li>
        <li>El contenido no infringe derechos de autor, marcas registradas, patentes ni derechos de imagen de terceros.</li>
        <li>Nos otorgás una licencia limitada, no exclusiva y revocable para mostrar ese contenido dentro de la plataforma mientras mantengas tu cuenta activa.</li>
      </ul>
      <p>
        Si publicás contenido sin los derechos correspondientes, podemos quitarlo, suspender o cancelar
        tu cuenta, y vos respondés ante el titular del derecho y ante terceros por cualquier reclamo.
      </p>

      <h2>5. Contenido prohibido</h2>
      <p>No está permitido publicar, ofrecer ni enlazar contenido que:</p>
      <ul>
        <li>Sea ilegal o promueva actividades ilegales (venta de productos prohibidos, falsificados, robados o sin habilitación).</li>
        <li>Infrinja derechos de autor, marcas u otra propiedad intelectual de terceros.</li>
        <li>Constituya fraude, engaño o publicidad engañosa hacia compradores.</li>
        <li>Contenga malware, phishing o intente capturar datos de terceros.</li>
        <li>Incite al odio, la violencia o la discriminación.</li>
        <li>Involucre explotación o abuso de menores, o cualquier material de esa naturaleza.</li>
        <li>Exponga datos personales de terceros sin su consentimiento.</li>
        <li>Sea spam, contenido automatizado masivo o que degrade el funcionamiento de la plataforma.</li>
      </ul>

      <h2>6. Denuncias de copyright y contenido ilegal</h2>
      <p>
        Si sos titular de un derecho (autor, marca, imagen u otro) o detectás contenido ilegal dentro de
        DAVENT, podés reportarlo desde
        <RouterLink to="/denuncias">el formulario de denuncias</RouterLink>, disponible también para
        personas sin cuenta. Cada denuncia debe incluir:
      </p>
      <ul>
        <li>Tus datos de contacto y la URL exacta del contenido denunciado.</li>
        <li>La obra, marca o derecho original afectado (en denuncias de copyright o marca).</li>
        <li>Una descripción clara y una declaración de buena fe sobre la veracidad del reporte.</li>
      </ul>
      <p>
        Revisamos cada denuncia y podemos solicitar información adicional. Si la denuncia es válida,
        quitamos el contenido y notificamos al comercio responsable. Las denuncias falsas o abusivas
        también pueden derivar en medidas sobre la cuenta denunciante.
      </p>

      <h2>7. Moderación y suspensión</h2>
      <p>
        Podemos quitar contenido, suspender o cancelar cuentas que incumplan estos términos, con o sin
        aviso previo según la gravedad. Los reincidentes —quienes acumulen denuncias válidas por
        infracción de derechos— pierden el acceso a la plataforma de forma definitiva.
      </p>

      <h2>8. Suscripciones y pagos</h2>
      <p>
        El acceso a funciones completas requiere una suscripción paga. Los cobros se procesan a través de
        Mercado Pago: DAVENT no almacena datos de tarjetas. Los precios y condiciones de cada plan se
        muestran antes de contratar y pueden actualizarse con aviso previo.
      </p>

      <h2>9. Limitación de responsabilidad</h2>
      <p>
        DAVENT no es parte de las ventas que concretes con tus clientes ni controla el contenido que
        publican los comercios. No respondemos por infracciones cometidas por usuarios, pero actuamos
        sobre las denuncias válidas conforme a la sección 6. El servicio se ofrece "tal cual", dentro de
        los límites que permite la ley.
      </p>

      <h2>10. Legislación y jurisdicción</h2>
      <p>
        Estos términos se rigen por las leyes de la República Argentina. Cualquier controversia se
        somete a los tribunales competentes del domicilio de DAVENT, salvo norma de orden público
        en contrario.
      </p>

      <h2>11. Cambios a estos términos</h2>
      <p>
        Podemos actualizar este documento. Cuando lo hagamos, publicaremos la nueva versión con su fecha
        y, si el cambio es relevante, te lo notificaremos por correo o dentro de la plataforma. El uso
        continuado del servicio después de una actualización implica la aceptación de la nueva versión.
      </p>
    </article>
  </LegalLayout>
</template>
