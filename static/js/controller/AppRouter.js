/*jslint browser: true */

define([
	'jquery',
	'backbone',
	'views/ManagePublicationsView',
	'views/PublicationView',
	'views/EditContributorView',
	'views/EditSeriesTitleView',
	'models/PublicationModel',
	'models/PublicationCollection',
	'models/ContributorModel',
	'models/SeriesTitleModel'
], function ($, Backbone, ManagePublicationsView, PublicationView, EditContributorView, EditSeriesTitleView,
			 PublicationModel, PublicationCollection, ContributorModel, SeriesTitleModel) {
	"use strict";

	var appRouter = Backbone.Router.extend({
		routes: {
			'': 'managePublicationsView',
			'search': 'managePublicationsView',
			'publication' : 'publicationView',
			'publication/:pubId' : 'publicationView',
			'contributor' : 'editContributorView',
			'contributor/:contribId' : 'editContributorView',
			'seriesTitle' : 'editSeriesTitleView',
			'seriesTitle/:seriesTitleId' : 'editSeriesTitleView'
		},

		applicationContextDiv: '#main-content',

		/*
		 * Create a view a put in in the applicationContextDiv. This view becomes the router's currentView
		 * @param {Backbone.View} View - The view to create
		 * @param {Object} opts - options to use when creating the view
		 */
		createView: function (View, opts) {
			var newEl = $('<div />');

			this.removeCurrentView();
			$(this.applicationContextDiv).append(newEl);
			this.currentView = new View($.extend({
				el: newEl,
				router: this
			}, opts));

			return this.currentView;
		},

		/*
		 * Remove the currentView
		 */
		removeCurrentView: function () {
			if (this.currentView) {
				this.currentView.remove();
			}
		},

		managePublicationsView: function () {
			var collection = new PublicationCollection();
			this.createView(ManagePublicationsView, {
				collection : collection
			}).render();
		},

		publicationView : function(pubId) {
			var model = new PublicationModel();
			if (pubId) {
				model.set('id', pubId);
			}

			this.createView(PublicationView, {
				model : model
			}).render();
		},

		editContributorView : function(contribId) {
			var model = new ContributorModel();
			if (contribId) {
				model.set('contributorId', contribId);
			}

			this.createView(EditContributorView, {
				model : model
			}).render();
		},

		editSeriesTitleView : function(seriesTitleId) {
			var model = new SeriesTitleModel();
			if (seriesTitleId) {
				model.set('id', seriesTitleId);
			}
			this.createView(EditSeriesTitleView, {
				model : model
			}).render();
		}
	});

	return appRouter;
});