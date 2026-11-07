// static/js/site.js
/* global $ */
$(function () {
  // --- Sample story: preview with your own child's name ---------------------
  var $story = $(".story-text");
  if ($story.length) {
    var template = $story.data("template");
    var sampleName = $story.data("sample-name");

    var render = function (name) {
      var text = template.split("{name}").join(name || sampleName);
      $story.empty();
      $.each(text.split(/\n\s*\n/), function (_, para) {
        $("<p>").text(para).appendTo($story); // .text() keeps user input safe
      });
    };

    $("#try-name").on("input", function () {
      render($.trim($(this).val()).slice(0, 30));
    });
  }

  // --- Printable form: client checks + AJAX submit -------------------------
  var $form = $("#printable-form");
  if (!$form.length) return;

  var $message = $("#form-message");
  var $button = $form.find("button[type=submit]");

  var showErrors = function (errors) {
    $form.find(".field").removeClass("has-error").find(".error").text("");
    $.each(errors, function (field, list) {
      var $field = $form.find('[data-field="' + field + '"]');
      $field.addClass("has-error").find(".error").text(
        $.map(list, function (e) { return e.message; }).join(" ")
      );
    });
  };

  var clientErrors = function () {
    var errors = {};
    var name = $.trim($("#id_child_name").val());
    if (!name) errors.child_name = [{ message: "Please add your child's first name." }];
    var email = $.trim($("#id_email").val());
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) errors.email = [{ message: "Please check your email address." }];
    if (!$("#id_confirmed_parent").is(":checked")) {
      errors.confirmed_parent = [{ message: "Please confirm you're the parent or carer." }];
    }
    return errors;
  };

  $form.on("submit", function (event) {
    event.preventDefault();
    $message.attr("hidden", true).text("");

    var errors = clientErrors();
    if (!$.isEmptyObject(errors)) {
      showErrors(errors);
      return;
    }

    $button.prop("disabled", true).text("Writing your story...");

    $.ajax({
      url: window.location.href,
      method: "POST",
      data: $form.serialize(),
      dataType: "json",
      headers: { "X-Requested-With": "XMLHttpRequest" }
    })
      .done(function (data) {
        window.location.href = data.redirect;
      })
      .fail(function (xhr) {
        var data = xhr.responseJSON || {};
        showErrors(data.errors || {});
        if (data.message) {
          $message.text(data.message).removeAttr("hidden");
        } else if (!data.errors) {
          $message.text("Something went wrong. Please try again in a minute.").removeAttr("hidden");
        }
        $button.prop("disabled", false).text("Send my free story");
      });
  });
});
